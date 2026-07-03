# TrustGraph: Trust-Aware Personal AI Companion Layer for Cognee

TrustGraph is a trust-aware memory layer that wraps around [Cognee](https://github.com/topoteretes/cognee) (an LLM-powered cognitive architecture and knowledge graph system). It tracks, scores, and resolves factual statements based on **recency**, **reinforcement**, **consistency**, and **contradiction resolution**. 

The app features a **modern Next.js 16/React 19 SPA dashboard** with interactive force-directed graph rendering, browser-native Text-to-Speech (TTS) & Speech-to-Text (STT), document ingestion with self-improvement, and factual claim verification.

---

## Table of Contents
1. [How It Works](#how-it-works)
2. [Mathematical Formula](#mathematical-formula)
3. [Core Components](#core-components)
4. [Modern Next.js Frontend Features](#modern-nextjs-frontend-features)
5. [Factual Claim & Web Verification](#factual-claim--web-verification)
6. [API Endpoints](#api-endpoints)
7. [Running the Application](#running-the-application)

---

## How It Works

TrustGraph manages factual claims by structuring unstructured text into entities and relation triples. When text is received:
1. **Extraction**: The system extracts subject-predicate-object facts.
2. **Contradiction Detection**: It checks new facts against stored facts to detect contradictions (either exact slot mismatches or semantic contradictions evaluated via LLM).
3. **Storage & Cognee Integration**: Non-conflicting facts are written to Cognee's vector and graph indexes, and the local trust metadata is saved. If a contradiction is detected, both facts are flagged as `contradicted` and their trust levels degrade.
4. **Scoring**: A composite trust score (between `0.0` and `1.0`) is dynamically computed for every fact.
5. **Decay**: Facts that are not reinforced over time decay and eventually get deactivated.
6. **Resolution**: Users can resolve contradictions by choosing a winning fact, which is reinforced while the losing fact is deleted (forgotten) from Cognee.

---

## Mathematical Formula

The trust score of a fact $T$ is computed dynamically in [trust_scorer.py](file:///d:/hackathon/cognee/trustgraph/trust_scorer.py) using a weighted combination of three components:

$$T = w_{\text{recency}} \cdot R + w_{\text{reinforce}} \cdot Re + w_{\text{consistency}} \cdot C$$

Where the default weights are:
*   $w_{\text{recency}} = 0.55$
*   $w_{\text{reinforce}} = 0.35$
*   $w_{\text{consistency}} = 0.10$

### 1. Recency Component ($R$)
Models the natural decay of memory over time. Facts become less trusted as time passes without reinforcement.
$$R = e^{-\lambda \cdot t_{\text{days}}}$$

### 2. Reinforcement Component ($Re$)
Models confidence gained by hearing the same claim multiple times.
$$Re = 1 - e^{-\alpha \cdot n}$$

### 3. Consistency Component ($C$)
Measures structural and semantic alignment with the rest of the database.
*   **Resolved** facts: $C = 0.0$
*   **Contradicted** or **Decayed** facts: $C = 0.5$
*   **Consistent** facts: $C = 1.0$

---

## Core Components

The codebase is organized in the [trustgraph/](file:///d:/hackathon/cognee/trustgraph) folder:

*   **[models.py](file:///d:/hackathon/cognee/trustgraph/models.py)**: Defines Pydantic data schemas representing `TrustMetadata`, `TrustScore`, `ContradictionPair`, and API query models.
*   **[fact_extractor.py](file:///d:/hackathon/cognee/trustgraph/fact_extractor.py)**: Extracts structured triples from free-form user statements using LiteLLM.
*   **[contradiction_detector.py](file:///d:/hackathon/cognee/trustgraph/contradiction_detector.py)**: Measures token overlap and calls LLM to check if two facts semantically contradict.
*   **[trust_scorer.py](file:///d:/hackathon/cognee/trustgraph/trust_scorer.py)**: Implements the composite trust scoring calculations.
*   **[trust_memory.py](file:///d:/hackathon/cognee/trustgraph/trust_memory.py)**: Coordinates fact workflows, manages the `.trustgraph/facts.json` local store, and invokes Cognee memory actions. Integrates dynamic `@cognee.agent_memory` decorators for session tracking.
*   **[api.py](file:///d:/hackathon/cognee/trustgraph/api.py)**: FastAPI REST backend containing endpoints for chat history, file uploads, and stats.

---

## Modern Next.js Frontend Features

Our state-of-the-art Single Page App (React 19 + Next.js 16 + Tailwind CSS v4) features:
*   **💬 Dynamic Multi-Chat History**: Creates chat sessions with unique UUIDs. Easily create new sessions (`➕ New`) or select past chats in the left sidebar.
*   **🔗 Interactive force-directed Vis.js Graph**: High-performance interactive visualization colored by trust level (Green: high, Yellow: medium, Red: low). Active contradictions are rendered as red diamonds with dashed red edges.
*   **🎙️ Native Voice Input (STT)**: Dictate prompts using browser-native Speech Recognition directly in the chat bar.
*   **🔊 Read-Aloud Option (TTS)**: Let the AI speak its responses aloud with a clean speaker toggle next to each chat bubble.
*   **📂 Ingest Document with Self-Improvement**: Drag/select a document, upload it, and watch the app trigger `cognee.remember(..., self_improvement=True)` to dynamically improve memory index alignment.

---

## Factual Claim & Web Verification

*   **Factual Verification**: The backend parses all facts originating from uploaded documents (source = `"document"`). When the user makes a statement, the backend verifies it against document facts. If the user makes an invalid claim, the assistant tells them they are wrong and explains why.
*   **Web Verification**: For any question or fact, the assistant executes a real-time web search (using Tavily or DuckDuckGo) to cross-reference answers, including citations, titles, and URLs.

---

## API Endpoints

FastAPI runs on `http://localhost:8001` (or `8000`) by default.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/store` | Extract and store facts from input text; flags contradictions. |
| `POST` | `/api/query` | Retrieve relevant trust-ranked facts for a query text. |
| `GET` | `/api/facts` | List all stored facts with detailed trust breakdowns. |
| `GET` | `/api/stats` | Retrieve total memory sizes, active facts, and contradiction counts. |
| `GET` | `/api/contradictions` | List all active, unresolved contradictions. |
| `POST` | `/api/resolve` | Resolve a contradiction group by picking a winner or keeping both. |
| `POST` | `/api/reinforce` | Manually increase the reinforcement count of a specific fact. |
| `POST` | `/api/decay` | Scan all facts and mark those below the decay threshold as decayed. |
| `POST` | `/api/reset` | Clear all local metadata and wipe the Cognee database. |
| `GET` | `/api/graph` | Fetch graph-friendly node and edge data. |
| `POST` | `/api/upload` | Ingest files using `cognee.remember(self_improvement=True)`. |
| `GET` | `/api/chat/sessions` | List active chat histories with message counts. |
| `POST` | `/api/chat/sessions` | Create a new chat session UUID. |
| `POST` | `/api/chat/sessions/{id}/messages` | Append a message, query memory, and trigger agent memory trace generation. |

---

## Running the Application

### 1. Start the FastAPI backend
Navigate to the repository root directory (`/mnt/d/hackathon/cognee` or `d:\hackathon\cognee`) and run:
```bash
.venv/bin/uvicorn trustgraph.api:app --reload --host 127.0.0.1 --port 8001
```

### 2. Start the Next.js Frontend
Navigate to the `trustgraph` directory:
```bash
cd trustgraph
pnpm dev
```
Open **`http://localhost:3000`** in your browser, head to the **Settings (⚙️)** page, and update the API base URL to **`http://localhost:8001`**.

