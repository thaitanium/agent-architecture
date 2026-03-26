# Agent Architecture

Production-ready multi-agent system for AI-powered application development using Claude Opus 4.6.

Implements Anthropic's best-practice harness design: a **Planner → Generator → Evaluator** pipeline with sprint-contract negotiation, live Playwright-based QA, context-reset handling, and full cost tracking.

---

## Architecture

```
User Requirement
      │
      ▼
ProductManagerAgent       expands to full product spec (MoSCoW)
      │
      ▼
TechnicalArchitectAgent   designs full stack architecture + API spec
      │
      ▼
DatabaseAgent             designs PostgreSQL schema + Alembic migrations
      │
      ▼
  Sprint Loop (1..N)
    Contract Negotiation:
      FrontendBuilder proposes contract
      QATestingAgent reviews it
      FrontendBuilder revises (if needed)
    Build:
      FrontendBuilderAgent  React/Vite/Tailwind/Zustand
      BackendBuilderAgent   FastAPI/SQLAlchemy/JWT
    QA (with retries):
      QATestingAgent uses Playwright to navigate live app
      Grades each criterion PASS / FAIL / PARTIAL
      Bugs fed back to builders for fixes
      │
      ▼
CodeQualityAgent          final security + performance code review
      │
      ▼
WorkflowExecution (full cost + token report)
```

---

## Agents

| Agent | Role | Thinking |
|---|---|---|
| `ProductManagerAgent` | Expands prompt to full spec (MoSCoW) | Yes |
| `TechnicalArchitectAgent` | Full stack architecture + API spec | Yes |
| `DatabaseAgent` | PostgreSQL schema + Alembic migrations | Yes |
| `FrontendBuilderAgent` | React 18 + Vite + Tailwind + Zustand | Yes |
| `BackendBuilderAgent` | FastAPI + SQLAlchemy + JWT | Yes |
| `QATestingAgent` | Live Playwright QA (skeptical evaluator + few-shot calibration) | Yes |
| `CodeQualityAgent` | Security + performance code review | No |
| `WorkflowOrchestrator` | Sequences all agents, tracks cost | — |

---

## Quick Start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
```

```python
from agents.orchestrator import WorkflowOrchestrator

orch = WorkflowOrchestrator(
    max_sprints=3,
    qa_retries=2,
    enable_playwright=False,  # set True when your app is live at app_url
)
result = orch.run(
    user_requirement="Build a 2D retro game maker with level editor and sprite editor",
    app_url="http://localhost:5173",
)
print(f"Done! Tokens: {result.total_tokens_used:,} | Est. cost: ${result.total_cost:.2f}")
```

---

## Key Best Practices Implemented

**Correct Anthropic SDK parameters** — Extended thinking uses `betas=["interleaved-thinking-2025-05-14"]` and `thinking={"type":"enabled","budget_tokens":N}`. Structured outputs use forced tool calls (`tool_choice: {"type":"tool"}`), not the non-existent `output_config.format`.

**Generator / Evaluator separation** — `QATestingAgent` is entirely separate from builder agents. It is prompted to be skeptical and calibrated with few-shot examples contrasting lazy approvals with evidence-based PASS verdicts.

**Sprint contract negotiation** — Before any code is written per sprint, the `FrontendBuilderAgent` proposes a contract (features + testable acceptance criteria) and `QATestingAgent` reviews and approves it. Both agree on "done" before building starts.

**Context-reset handling** — `BaseAgent` monitors input tokens. When a session approaches 75% of the 200k context window it generates a structured `HandoffArtifact` and returns it. The orchestrator constructs a fresh agent and passes the artifact so work resumes seamlessly.

**Full cost tracking** — Every agent session accumulates `input_tokens` and `output_tokens`. The orchestrator rolls these into `WorkflowExecution.total_tokens_used` and `total_cost` (Opus 4.6 pricing: $15/M input, $75/M output).

**Live browser QA** — `QATestingAgent` accepts Playwright MCP tools. When `enable_playwright=True` the orchestrator injects `playwright_navigate`, `playwright_click`, `playwright_fill`, `playwright_screenshot`, and `playwright_evaluate` so the agent interacts with the running app rather than reasoning about code statically.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover: `AgentState` persistence, `HandoffArtifact` prompt generation, structured output tool construction, context-reset threshold logic, correct SDK parameters (no `output_config.format`, correct `betas`/`thinking` fields), token accumulation, and end-to-end `run()` with mocked API responses.

---

## Project Structure

```
agent-architecture/
├── agents/
│   ├── core/
│   │   └── base_agent.py           BaseAgent, AgentState, HandoffArtifact
│   ├── specialized/
│   │   ├── product_manager.py
│   │   ├── technical_architect.py
│   │   ├── database_agent.py
│   │   ├── frontend_builder.py
│   │   ├── backend_builder.py
│   │   ├── qa_testing.py           Playwright tools injection + few-shot calibration
│   │   ├── code_quality.py
│   │   └── ai_specialist.py
│   └── orchestrator.py             WorkflowOrchestrator
├── schemas/
│   └── structured_schemas.py       Pydantic output models for all agents
├── tests/
│   └── test_base_agent.py          Unit tests (no API key required)
├── docs/
│   └── BEST_PRACTICES_GUIDE.md
├── prompts/
│   └── prompt_templates.md
├── config/
│   └── agent_config.json
├── requirements.txt
└── README.md
```

---

## References

- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- - [Anthropic: Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)
  - - [Anthropic: Context Engineering](https://www.anthropic.com/engineering/context-engineering)
    - 
