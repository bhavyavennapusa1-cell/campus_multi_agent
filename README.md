# Campus multi-agent AI system — AgentX 2026

A multi-agent smart campus assistant built for the AgentX hackathon. An
orchestrator agent plans and routes user requests across four specialized
agents (academic, placement, campus services, communication), backed by a
shared knowledge agent (RAG over sample institutional documents) and a
memory store.

## Folder structure

```
orchestrator/    Uday Veena - planning + dispatch loop
agents/          Sivani Vadrevu - academic, placement, campus, communication agents
knowledge/       Bhavya Vennapusa - RAG (rag.py) and memory (memory.py)
frontend/        Suhani Patel - HTML/CSS/JS frontend UI + live trace panel
data/            Mock JSON/SQLite data (student records, internships, events)
shared/          The contract everyone codes against (schemas.py)
```

## Setup

```
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

pip install -r requirements.txt

cp .env.example .env          # then fill in your real API key in .env
```

## Running it

```
python main.py
```
Or run uvicorn directly:
```
uvicorn main:app --reload --port 8000
```
Then navigate to `http://localhost:8000` in your web browser.

## Architecture

User request → Orchestrator agent (plans + routes) → Academic / Placement /
Campus / Communication agents → shared Knowledge agent (RAG) + Memory store →
mock APIs / JSON / SQLite data layer.

## Team

- Orchestrator & planning: Uday Veena
- Specialized agents: Sivani Vadrevu
- Knowledge (RAG) & memory: Bhavya Vennapusa
- Frontend & demo: Suhani Patel
