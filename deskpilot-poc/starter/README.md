# DeskPilot - AI IT Help Desk (Microsoft Foundry)

DeskPilot answers IT questions from a company knowledge base and manages support tickets.
It is a multi-agent system built only with the Microsoft Foundry SDK (`azure-ai-projects`) and the OpenAI Responses API.

![Architecture](docs/architecture.png)

## What it does
- **Triage agent** classifies each message: `knowledge`, `ticket`, `unsafe` or `other`.
- **Knowledge agent** answers from 10 IT articles through a Foundry IQ knowledge base (Azure Blob Storage + Azure AI Search) and cites its sources.
- **Ticket agent** creates and reads tickets with custom functions, lists and updates tickets through a local MCP server, and draws charts with the code interpreter.
- **Guardrails**: a Foundry content filter, a prompt-injection triage rule, and access control enforced in code (employees see only their own tickets).
- **Evaluation**: 20 questions measure routing, tool use, grounding and guardrails.

## Project layout
| Folder | Purpose |
| --- | --- |
| `01_model_eval`, `02_chat_baseline`, `03_guardrails` | Day 1 scripts: compare models, chat with streaming and a tool, red-team the guardrail |
| `common/` | Settings, clients, ticket database, functions, MCP client, judge helper |
| `mcp_server/` | The ticket MCP server (FastMCP, stdio) |
| `agents/` | Agent definitions and the orchestrator |
| `app.py` | Streamlit UI |
| `evaluation/` | Evaluation questions and runner |
| `data/` | Knowledge articles (`kb_src` Markdown, `kb` PDF) and 30 seed tickets |
| `tests/` | Offline tests for ticket rules |

## Setup
Requires Python 3.13, Azure CLI, and a Microsoft Foundry project with a `gpt-5` deployment and `text-embedding-3-small`.

```
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # fill in the endpoints and deployment names
az login
python scripts/check_connection.py
python scripts/generate_kb_pdfs.py   # creates data/kb/*.pdf to upload to Blob Storage
python scripts/seed_db.py --reset
```

Create the knowledge agent in the Foundry portal (see the lab guide, step 2.1), then:

```
python agents/create_agents.py
streamlit run app.py
```

## Tests and evaluation
```
pytest -q                              # offline
python scripts/seed_db.py --reset
python evaluation/run_eval.py          # needs Azure; writes evaluation/results.md
```

## Design decisions
- **Identity is injected by code.** The model never supplies `requester`; the app passes the signed-in user, and `common/db.py` enforces the rules.
- **Knowledge stays managed.** Retrieval, chunking and indexing are handled by Foundry IQ, so the code only references the agent by name.
- **Local MCP server.** Ticket listing and updates are exposed over MCP (stdio); the same server could later be hosted remotely.
- **Cost.** Delete the agents with `python agents/delete_agents.py --all` and remove the Azure resources when you finish.

## Results
Paste your numbers from `evaluation/results.md` here.
