# TrustGraph: Trust-Aware Memory Layer for Cognee

TrustGraph is a lightweight, trust-aware memory layer that wraps around [Cognee](https://github.com/topoteretes/cognee) (an LLM-powered cognitive architecture and knowledge graph system). It tracks, scores, and resolves factual statements based on **recency**, **reinforcement**, **consistency**, and **contradiction resolution**.

---

## Table of Contents
1. [How It Works](#how-it-works)
2. [Mathematical Formula](#mathematical-formula)
3. [Core Components](#core-components)
4. [Applications and Use Cases](#applications-and-use-cases)
5. [API Endpoints](#api-endpoints)
6. [Example of Use](#example-of-use)
7. [Running the Application](#running-the-application)

---

## How It Works

TrustGraph manages factual claims by structuring unstructured text into entities and relation triples. When a new text is received:
1. **Extraction**: The system extracts subject-predicate-object facts.
2. **Contradiction Detection**: It checks the new facts against already-stored facts to detect contradictions (either exact matching slots or semantic contradictions evaluated via LLM).
3. **Storage & Cognee Integration**: Non-conflicting facts are written to Cognee's vector and graph indexes, and the local trust metadata is saved. If a contradiction is detected, both conflicting facts are flagged as `contradicted` and their trust levels degrade.
4. **Scoring**: A composite trust score (between `0.0` and `1.0`) is dynamically computed for every fact whenever they are queried.
5. **Decay**: Facts that are not reinforced over time decay and eventually get deactivated.
6. **Resolution**: Users (or external systems) can resolve contradictions by choosing a winning fact, which is reinforced while the losing fact is deleted (forgotten) from Cognee.

---

## Mathematical Formula

The trust score of a fact $T$ is computed dynamically in [trust_scorer.py](file:///d:/hackathon/cognee/trustgraph/trust_scorer.py) using a weighted combination of three components:

$$T = w_{\text{recency}} \cdot R + w_{\text{reinforce}} \cdot Re + w_{\text{consistency}} \cdot C$$

Where the default weights are:
*   $w_{\text{recency}} = 0.4$
*   $w_{\text{reinforce}} = 0.35$
*   $w_{\text{consistency}} = 0.25$

The final score $T$ is clamped between `0.0` and `1.0`.

### 1. Recency Component ($R$)
Models the natural decay of memory over time. Facts become less trusted as time passes without reinforcement.
$$R = e^{-\lambda \cdot t_{\text{days}}}$$
*   $t_{\text{days}}$: Time in days since the fact was stored or reinforced.
*   $\lambda$ (`recency_lambda`): Decay speed coefficient (default: `0.1`).

### 2. Reinforcement Component ($Re$)
Models confidence gained by hearing the same claim multiple times.
$$Re = 1 - e^{-\alpha \cdot n}$$
*   $n$: Number of times the fact has been reinforced.
*   $\alpha$ (`reinforcement_alpha`): Scaling factor (default: `0.5`).

### 3. Consistency Component ($C$)
Measures structural and semantic alignment with the rest of the database.
*   **Resolved** facts: $C = 0.0$
*   **Contradicted** or **Decayed** facts: $C = 0.5$
*   **Conflict detected** (same Subject and Predicate but different Object): $C = 0.5$
*   **Consistent** facts (no conflicts found): $C = 1.0$

---

## Core Components

The codebase is organized in the [trustgraph/](file:///d:/hackathon/cognee/trustgraph) folder:

*   **[models.py](file:///d:/hackathon/cognee/trustgraph/models.py)**: Defines Pydantic data schemas representing `TrustMetadata`, `TrustScore`, `ContradictionPair`, and API query models.
*   **[fact_extractor.py](file:///d:/hackathon/cognee/trustgraph/fact_extractor.py)**: Extracts structured triples from free-form user statements using LiteLLM (with a regex-based fallback heuristic).
*   **[contradiction_detector.py](file:///d:/hackathon/cognee/trustgraph/contradiction_detector.py)**: 
    *   *Exact Contradictions*: Scans for matching slots `(subject, predicate)` with differing `object_value`.
    *   *Semantic Contradictions*: Measures token overlap (Jaccard similarity $\ge 0.35$) and calls the LLM to inspect if two facts semantically contradict.
*   **[trust_scorer.py](file:///d:/hackathon/cognee/trustgraph/trust_scorer.py)**: Implements the composite trust scoring calculations.
*   **[trust_memory.py](file:///d:/hackathon/cognee/trustgraph/trust_memory.py)**: Coordinates fact workflows, manages the `.trustgraph/facts.json` local store, and invokes Cognee memory actions (`remember`, `recall`, `improve`, `forget`).
*   **[api.py](file:///d:/hackathon/cognee/trustgraph/api.py)**: Provides FastAPI REST endpoints to integrate with external applications.
*   **[chat_app.py](file:///d:/hackathon/cognee/trustgraph/chat_app.py)**: A Streamlit-based graphical frontend allowing interactive storage, retrieval, decay triggering, and contradiction resolution.

---

## Applications and Use Cases

1.  **AI Assistant Personalization**: Helps virtual assistants adapt to changing user preferences (e.g., "I moved to Berlin" vs. "I live in Munich") without getting confused by outdated facts.
2.  **Collaborative Knowledge Sharing**: Aggregates information from multiple agents/users. When assertions clash, they are flagged for human verification or resolved programmatically based on source authority.
3.  **Data Quality Guardrails**: Serves as a consistency check for Retrieval-Augmented Generation (RAG) contexts, ranking highly-trusted, consistent facts above disputed ones.

---

## API Endpoints

FastAPI runs on `http://localhost:8000` by default.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/store` | Extract and store facts from input text; flags contradictions. |
| `POST` | `/api/query` | Retrieve relevant trust-ranked facts for a query text. |
| `GET` | `/api/facts` | List all stored facts with detailed trust breakdowns. |
| `GET` | `/api/contradictions` | List all active, unresolved contradictions. |
| `POST` | `/api/resolve` | Resolve a contradiction group by picking a winner or keeping both. |
| `POST` | `/api/reinforce` | Manually increase the reinforcement count of a specific fact. |
| `POST` | `/api/decay` | Scan all facts and mark those below the decay threshold as decayed. |
| `POST` | `/api/reset` | Clear all local metadata and wipe the Cognee database. |
| `GET` | `/api/graph` | Fetch graph-friendly node and edge data. |

---

## Example of Use

### Step 1: Store a fact
You send: `"My favourite programming language is Python."`
*   **Extracted**: `(subject="my favourite programming language", predicate="is", object_value="Python")`
*   **Trust Score**: `~0.65` (100% consistent, no reinforcement yet, max recency).

### Step 2: Store a conflicting fact
You send: `"My favourite programming language is Rust."`
*   **Extracted**: `(subject="my favourite programming language", predicate="is", object_value="Rust")`
*   **Contradiction Detected**: Same subject and predicate, but different object value.
*   **Result**: Both facts are marked `contradicted`. Their consistency components drop to `0.5`, lowering their trust scores.

### Step 3: Resolve the contradiction
You run a resolution requesting to keep the second fact (`winner_id` = Rust's ID).
*   **Rust fact**: Status updated to `active`, reinforcement count incremented, trust score rebounds.
*   **Python fact**: Status changed to `resolved`, deleted from Cognee memory.

---

## Running the Application

### 1. Start the FastAPI backend
```bash
uvicorn trustgraph.api:app --reload
```

### 2. Start the Streamlit frontend
```bash
streamlit run trustgraph/chat_app.py
```
