# Strategic Research Agent (SRA)

A production-grade autonomous research system. You give it a research question
("Should I build an AI startup for dentists?"); it plans, gathers evidence,
reflects, self-critiques, and produces a cited professional report.

**Not** a chatbot, not a prompt chain. The LLM decides *what* to investigate;
the runtime decides *how* research is executed, validates every action, and
owns budgets, state, and recovery.

## Architecture at a glance

```
API/CLI -> Research Runtime (state machine + decision loop)
             |- Planner            what to investigate, plan revisions
             |- Task Manager       prioritized queue of investigations
             |- Research Engine    proposes next validated AgentAction
             |- Tool Registry      pluggable tools (search, read, parse, ...)
             |- Memory Manager     working + long-term memory
             |- Knowledge Store    structured facts/claims/stats (DuckDB)
             |- Reflection Engine  per-step strategy evaluation
             |- Critic             hard gate before any report
             |- Confidence         per-topic scores drive continue/stop
             |- Budget Manager     iterations, tokens, cost, time, sources
             |- Checkpoint Manager crash-safe snapshots per state transition
             |- Report Generator   Markdown / HTML / PDF / JSON
```

Design rules:

- The runtime owns execution; the LLM owns reasoning.
- Every LLM-proposed action is schema-validated before it runs.
- No hardcoded research workflows.
- Structured knowledge, never raw-text-only memory.

## Repository layout

```
sra/
  core/           run context, ports (protocols), errors, state enum
  models/         Pydantic domain models shared across packages
  runtime/        decision loop, DI container, action validator
  planner/        goal -> ResearchPlan, plan revision
  tasks/          task manager (prioritized investigation queue)
  research/       research engine (action proposer)
  tools/          tool protocol, registry, tool implementations
  memory/         working + long-term memory
  knowledge/      extraction pipeline + DuckDB knowledge store
  reflection/     post-step reflection engine
  critic/         pre-report critique gate
  confidence/     per-topic confidence estimation
  reporting/      report generation (md/html/pdf/json)
  budget/         budget ledger + enforcement
  checkpoint/     snapshot persistence + resume
  observability/  execution logger (human-readable + structured)
  storage/        SQLite / DuckDB adapters
  api/            FastAPI app (thin; no agent logic)
  cli/            CLI entrypoint (wraps the same application service)
tests/
  unit/
  integration/
```

## Getting started

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install with dev tooling
pip install -e ".[dev]"

# 3. Install the Playwright browser used by the website reader / PDF export
playwright install chromium

# 4. Configure secrets
Copy-Item .env.example .env   # then edit .env
```

## Quality gates

```powershell
ruff check .          # lint
ruff format .         # format
mypy sra              # strict type-checking
pytest                # unit tests
pytest -m integration # network/storage integration tests
```

## Docker

```powershell
docker build -t sra .
docker run --env-file .env -p 8000:8000 sra
```

## Status

Phase 2 of 12: repository skeleton and tooling. Interfaces (Phase 3) land next;
packages are intentionally empty until their phase.
