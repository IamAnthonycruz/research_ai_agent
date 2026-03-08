# Research AI Agent

A multi-tool research agent built from scratch with Google's Gemini 2.0 Flash API. The agent takes a research topic, autonomously searches the web, and returns structured, source-backed findings.

This project follows a ground-up approach — no frameworks like LangChain or CrewAI. Every component (tool routing, execution, structured output) is built manually to understand the core patterns behind modern AI agent systems.

## Current Progress

**Part 1: One Agent, One Tool** (In Progress — 4/5 subproblems complete)

- [x] **1.1 — API Integration**: Gemini client setup with environment-based key management and error handling
- [x] **1.2 — Function Declarations**: Tool definitions using Gemini's `types.FunctionDeclaration` with optimized descriptions for reliable tool selection
- [x] **1.3 — Tool Execution**: Async DuckDuckGo search handler with full function call → function response loop
- [x] **1.4 — Structured Output**: Pydantic-validated JSON responses with enforced schema via Gemini's `response_schema`
- [ ] **1.5 — Agent Loop**: ReAct-style loop with system prompt, iteration limits, and conversation history management

## Architecture

```
User Query
  │
  ▼
Gemini 2.0 Flash (with tool declarations)
  │
  ├── decides to search ──→ DuckDuckGo async handler ──→ results fed back
  │
  └── decides to respond ──→ structured output (Pydantic-enforced JSON)
                               │
                               ▼
                        WebSearchResponse
                        ├── title: str
                        ├── summary: str
                        ├── key_findings: list[str]
                        └── sources: list[Sources]
                               ├── title: str
                               └── url: HttpUrl
```

## Project Structure

```
src/research_agent/
├── tools/
│   ├── definitions.py      # Tool declarations (function schemas for the model)
│   └── handlers.py         # Tool execution (async search implementation)
├── schemas/
│   └── web_search_schema.py # Pydantic models for structured output
├── agent.py                 # Agent loop, tool routing, orchestration
└── client.py                # Gemini client, configs, structured output builder
```

## Setup

### Prerequisites
- Python 3.12+
- [Gemini API key](https://aistudio.google.com/apikey)

### Installation

```bash
git clone https://github.com/<your-username>/Research-AI-Agent.git
cd Research-AI-Agent
pip install -e .
```

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

### Run

```bash
python -m research_agent.agent
```

## Key Dependencies

- `google-genai` — Gemini API SDK (unified, not the older `google-generativeai`)
- `asyncddgs` — Async DuckDuckGo search (no API key required)
- `pydantic` — Schema validation and structured output enforcement
- `python-dotenv` — Environment variable management

## Roadmap

This agent is being built incrementally toward a full multi-agent research system:

| Part | Description | Status |
|------|-------------|--------|
| 1 | One Agent, One Tool | In Progress |
| 2 | One Agent, Multiple Tools (fetch, scratchpad) | Upcoming |
| 3 | RAG (embeddings, vector search, retrieval) | Upcoming |
| 4 | Evaluation Suite (LLM-as-judge) | Upcoming |
| 5 | Two Agents + Orchestrator | Upcoming |
| 6 | Full Multi-Agent System (Planner → Researchers → Synthesizer → Reviewer) | Upcoming |

## License

MIT
