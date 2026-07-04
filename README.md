# TrustGraph

TrustGraph is a trust-aware memory and chat application that combines a FastAPI backend with a modern Next.js frontend. It stores facts, scores them by recency, reinforcement, and consistency, detects contradictions, and exposes the data through a dashboard for chatting, browsing facts, viewing the graph, and configuring the backend.

## What is included

- A FastAPI backend with endpoints for memory, chat sessions, contradictions, graph data, and stats
- A Next.js 16 + React 19 + Tailwind CSS frontend with four main pages:
  - /chat
  - /facts
  - /graph
  - /settings
- Local JSON-backed memory data in the data folder
- Optional LLM-backed answer generation when a compatible model is configured

## Current project structure

- api.py: FastAPI application and API routes
- trust_memory.py: memory/query/reinforcement/answer generation logic
- models.py: Pydantic models for facts, scores, contradictions, and results
- fact_extractor.py: fact extraction logic
- contradiction_detector.py: contradiction detection logic
- trust_scorer.py: trust scoring logic
- visualization.py: graph export helpers
- app/: Next.js app router pages and layout
- components/: React UI components such as the sidebar and trust badge
- lib/: API client helpers and utility functions
- data/: stored facts and chat sessions

## Tech stack

- Backend: FastAPI, Pydantic, Uvicorn
- Frontend: Next.js, React, Tailwind CSS
- Data: JSON files in the data folder
- Optional LLM integration: LiteLLM / model-backed answer generation

## Environment setup

Create or update a .env file in the project root with the model settings you want the backend to use.

Example:

```env
LLM_PROVIDER="custom"
LLM_MODEL="groq/llama-3.3-70b-versatile"
LLM_API_KEY="your-key"
EMBEDDING_PROVIDER="fastembed"
EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS=384
```

If no usable model is configured, the backend will fall back to a simpler local response path instead of crashing.

## Running the backend

Open a terminal in the project folder and run:

### Windows CMD

```cmd
cd /d E:\TrustGraph
call .\.venv\Scripts\activate.bat
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

### Bash

```bash
cd /e/TrustGraph
source .venv/Scripts/activate
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

The backend will be available at http://127.0.0.1:8000.

## Running the frontend

Open a second terminal and run:

### Windows CMD

```cmd
cd /d E:\TrustGraph
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

### Bash

```bash
cd /e/TrustGraph
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

The frontend will be available at http://127.0.0.1:3000.

## Build verification

You can verify the frontend build with:

```bash
npm run build
```

## API overview

The current backend exposes:

- GET /health
- POST /api/store
- POST /api/query
- GET /api/facts
- GET /api/stats
- GET /api/contradictions
- GET /api/resolutions
- POST /api/resolve
- POST /api/reinforce
- POST /api/decay
- POST /api/reset
- GET /api/graph
- POST /api/upload
- GET /api/chat/sessions
- POST /api/chat/sessions
- POST /api/chat/sessions/{session_id}/messages

## Notes

- The frontend uses the backend URL from the Settings page. The default target is http://localhost:8000.
- The app reads and writes local JSON data under the data folder.
- If you want richer AI responses, configure a working LLM provider and model in the environment.
