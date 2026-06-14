# 🕌 Ask Abu Dhabi

A multilingual (English / Arabic) AI tourism assistant for the Emirate of Abu
Dhabi. Ask about mosques, museums, beaches, transport, visas, and etiquette and
get a structured, source-linked answer tuned to your persona.

Built as a clean, testable, production-shaped Python application: thin entry
points, pure domain logic, dependency injection throughout, and a fully offline
test suite.

---

## Features

- **Multilingual EN/AR** — auto-detects Arabic script, or force a language.
- **Persona-aware** — `first_time`, `family`, and `business` tones.
- **Structured answers** — every reply follows a 4-section Markdown layout with
  a verbatim "What's Next" nudge.
- **Off-topic guardrail** — non-tourism queries are answered by a static
  redirect and **never** reach the LLM.
- **Pluggable LLMs** — OpenRouter and Gemini behind one interface.
- **Resilient knowledge base** — `FRESH → STALE → BASELINE → FAILED` fallback.
- **Self-updating** — a Firecrawl ETL pipeline refreshes the KB with atomic
  writes and an 8-of-12 validation gate.
- **Analytics** — every query is logged to SQLite.

---

## Architecture

```
app.py / api.py          thin entry points (no business logic)
        │
        ▼
core/orchestrator.py     process_query(request, provider, settings, attractions)
   detect_language → match_attraction → log analytics
   → off-topic? static reply : build_prompt → provider.generate → AskResponse
        │
        ├── core/config.py        Pydantic Settings (.env, no scattered getenv)
        ├── core/schema.py        Pydantic v2 boundary models
        ├── core/kb_loader.py     FRESH → STALE → BASELINE chain
        ├── core/knowledge_base.py attraction matching
        ├── core/intent.py        language + on-topic detection
        ├── core/prompts.py       EN/AR 4-section templates
        ├── core/analytics.py     SQLite query log
        └── core/exceptions.py    AskAbuDhabiError hierarchy

providers/   base.LLMProvider (ABC) → openrouter, gemini ; factory selects
ml/          optional sklearn intent classifier (keyword fallback)
etl/         sources → firecrawl_client → extractors → transformers
             → validators → pipeline (atomic publish) → run (CLI)
```

**Design rules enforced in the code**

1. No business logic in [app.py](app.py) / [api.py](api.py).
2. No global state — dependencies are injected.
3. Config only through [core/config.py](core/config.py).
4. Custom exception hierarchy in [core/exceptions.py](core/exceptions.py).
5. Pydantic v2 models for every cross-module structure ([core/schema.py](core/schema.py)).
6. LLM providers behind [providers/base.py](providers/base.py).
7. SQLite analytics for every query ([core/analytics.py](core/analytics.py)).
8. Off-topic queries bypass the LLM ([core/orchestrator.py](core/orchestrator.py)).
9. Atomic KB writes and an 8/12 validation gate ([etl/pipeline.py](etl/pipeline.py)).

---

## Quick start

```bash
# 1. Bootstrap (venv + deps + .env)
./scripts/setup.sh
source .venv/bin/activate

# 2. Add your keys
$EDITOR .env            # OPENROUTER_API_KEY or GEMINI_API_KEY, FIRECRAWL_API_KEY

# 3. Run the UI (or the API)
./scripts/run.sh ui     # http://localhost:8501
./scripts/run.sh api    # http://localhost:8000
```

No active knowledge base yet? The app automatically serves the bundled
[data/baseline_knowledge_base.json](data/baseline_knowledge_base.json) (status
`BASELINE`) so it works out of the box.

---

## Configuration

All settings live in [.env](.env.example) and are validated by
[core/config.py](core/config.py). Key variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_PROVIDER` | `openrouter` or `gemini` | `openrouter` |
| `OPENROUTER_API_KEY` / `GEMINI_API_KEY` | provider credentials | — |
| `OPENROUTER_MODEL` / `GEMINI_MODEL` | model id | per-provider |
| `KB_PATH` / `KB_BASELINE_PATH` | active vs bundled KB | `data/…` |
| `KB_STALE_AFTER_HOURS` | FRESH→STALE threshold | `168` |
| `ANALYTICS_DB_PATH` | SQLite analytics db | `data/analytics.db` |
| `FIRECRAWL_API_KEY` | ETL scraping | — |
| `ETL_MIN_VALID_SOURCES` | publish gate (of 12) | `8` |

---

## API

`./scripts/run.sh api` serves FastAPI on port 8000 (CORS open to the Streamlit
UI on `localhost:8501`).

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/ask` | Process a query → `AskResponse` |
| `GET` | `/health` | Liveness, provider, KB status |
| `GET` | `/attractions` | The loaded knowledge base |
| `GET` | `/analytics` | Aggregate query analytics |

```bash
curl -s localhost:8000/ask \
  -H 'content-type: application/json' \
  -d '{"query": "What are the opening hours of the Grand Mosque?", "persona": "first_time"}'
```

---

## Knowledge base & ETL

The active KB is a JSON document of 12 entries (attractions + travel topics).
The [ETL pipeline](etl/pipeline.py) refreshes it:

```bash
./scripts/refresh_kb.sh      # python -m etl.run
```

For each of the 12 [sources](etl/sources.py): Firecrawl `scrape` → `extract` →
`transform` → `validate`. If **≥ 8** entries validate, the new KB is written
**atomically** (temp file + `os.replace`). Otherwise the run aborts, the
existing KB is left untouched, and an `ETLError` is raised.

Loading uses a strict fallback chain ([core/kb_loader.py](core/kb_loader.py)):

| Status | Meaning |
| --- | --- |
| `FRESH` | active KB present and within the staleness window |
| `STALE` | active KB present but older than `KB_STALE_AFTER_HOURS` (served with a warning) |
| `BASELINE` | active KB missing/invalid → bundled baseline served |
| `FAILED` | neither active nor baseline could load (raises `KnowledgeBaseError`) |

---

## Testing

The suite is **fully offline** — all HTTP is mocked and ETL tests are
fixture-driven.

```bash
./scripts/test.sh            # or: python -m pytest
```

Coverage spans intent gating, prompt structure, both providers, the
orchestrator's off-topic bypass, the KB fallback chain, the FastAPI endpoints,
and the ETL extract/validate/publish stages (including atomic-abort).

---

## Docker

```bash
./scripts/deploy.sh          # docker compose build && up -d
```

Brings up the API (8000) and UI (8501) from a single
[Dockerfile](Dockerfile), with `./data` mounted for the KB and analytics db.

---

## Project layout

```
core/        domain logic (config, schema, kb, intent, prompts, analytics, orchestrator)
providers/   LLM providers (base, openrouter, gemini, factory)
ml/          optional intent classifier
etl/         Firecrawl ETL pipeline
data/        baseline (and generated) knowledge base + analytics db
tests/       offline test suite + fixtures
scripts/     setup / run / test / refresh_kb / deploy
```

---

## Tech stack

Python 3.11 · Streamlit · FastAPI · Pydantic v2 + pydantic-settings · requests ·
sqlite3 (stdlib) · scikit-learn (optional) · pytest + pytest-mock · Firecrawl.

Deliberately avoided: LangChain, vector databases, ORMs.

## License

MIT.
