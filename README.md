# Agent Architecture

Production-ready multi-agent system for AI-powered application development using Claude Opus 4.6 / Sonnet 4.6.

Implements Anthropic's best-practice harness design: a **Planner → Generator → Evaluator** pipeline
with sprint-contract negotiation, parallel builder execution, live Playwright-based QA,
context-reset handling, prompt caching, and full cost tracking.

---

## Architecture

```
User Requirement
      |
      ▼
ProductManagerAgent      expands to full product spec (MoSCoW)
      |
      ▼
TechnicalArchitectAgent  designs full stack architecture + API spec
      |
      ▼
DatabaseAgent            generates schema + migrations
      |
      ▼
Sprint Loop (up to N sprints)
  ├── sprint-contract negotiation
  ├── FrontendBuilderAgent ──┐  run IN PARALLEL (ThreadPoolExecutor)
  ├── BackendBuilderAgent  ──┘
  └── QATestingAgent           Playwright tests (retry up to qa_retries)
      |
      ▼
CodeQualityAgent         final security + quality review
```

---

## Agent Model Routing

| Agent | Model | Thinking | Effort |
|---|---|---|---|
| ProductManagerAgent | claude-opus-4-6 | ✅ adaptive | high |
| TechnicalArchitectAgent | claude-opus-4-6 | ✅ adaptive | high |
| FrontendBuilderAgent | claude-opus-4-6 | ✅ adaptive | high |
| BackendBuilderAgent | claude-opus-4-6 | ✅ adaptive | high |
| DatabaseAgent | claude-opus-4-6 | ✅ adaptive | medium |
| QATestingAgent | claude-opus-4-6 | ✅ adaptive | medium |
| **CodeQualityAgent** | **claude-sonnet-4-6** | ❌ disabled | — |

CodeQualityAgent routes to Sonnet 4.6 for cost efficiency — code review does not
require the deep reasoning needed for full-stack generation.

---

## Adaptive Thinking API

This project uses Anthropic's **adaptive thinking** mode (available on Opus 4.6 and Sonnet 4.6),
which lets the model decide how much reasoning to apply based on problem difficulty.

### Correct usage (current)

```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={"type": "adaptive"},          # adaptive, not "enabled"
    output_config={"effort": "high"},        # low | medium | high
    messages=[...],
)
```

### Deprecated usage (do NOT use)

```python
# ❌ WRONG — deprecated API, raises error on Opus/Sonnet 4.6
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    betas=["interleaved-thinking-2025-05-14"],
    messages=[...],
)
```

### EffortLevel enum

```python
from agents.core.base_agent import EffortLevel

EffortLevel.LOW    # "low"    — fast, cheaper
EffortLevel.MEDIUM # "medium" — balanced
EffortLevel.HIGH   # "high"   — deepest reasoning, most tokens
```

---

## tool_choice Constraint

When `thinking` is enabled, `tool_choice` **must** be `{"type": "auto"}`.
Using `{"type": "tool"}` alongside thinking raises an API error.

```python
# ✅ Correct when thinking is enabled
tool_choice = {"type": "auto"}

# ❌ Will cause API error when thinking is enabled
tool_choice = {"type": "tool", "name": "structured_output"}
```

`BaseAgent._build_api_params()` enforces this automatically.

---

## Prompt Caching

System prompts and tool definitions are wrapped with `cache_control: {"type": "ephemeral"}`
to enable Anthropic's prompt caching, reducing costs on repeated agent calls within a session.

```python
# System prompt block with cache_control
{
    "type": "text",
    "text": SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"}
}
```

Cached tokens are charged at ~10% of standard input token price.

---

## Parallel Builder Execution

`FrontendBuilderAgent` and `BackendBuilderAgent` run concurrently within each sprint
using `concurrent.futures.ThreadPoolExecutor`, cutting wall-clock time roughly in half.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    fe_future = executor.submit(frontend_builder.build_frontend, ...)
    be_future = executor.submit(backend_builder.build_backend, ...)
    frontend_code = fe_future.result()
    backend_code  = be_future.result()
```

---

## Streaming Threshold

The Anthropic API **requires streaming** when `max_tokens > 21,333` (= 64,000 / 3).
Builder agents currently use `max_tokens=16,000`, which is below the threshold and
does not require streaming. If you raise builder `max_tokens` above 21,333, switch
`BaseAgent.run()` to use `client.messages.stream()`.

---

## Thinking Block Continuity

When appending the assistant's response back to the conversation history, pass
`response["content"]` **unchanged** (including all thinking blocks). Stripping
thinking blocks breaks reasoning continuity across turns.

```python
# ✅ Correct — preserve thinking blocks
self.state.messages.append({"role": "assistant", "content": response.content})

# ❌ Wrong — strips thinking blocks, breaks multi-turn reasoning
self.state.messages.append({"role": "assistant", "content": text_only})
```

---

## Project Structure

```
agent-architecture/
├── agents/
│   ├── core/
│   │   └── base_agent.py          # BaseAgent, AgentConfig, EffortLevel, HandoffArtifact
│   ├── specialized/
│   │   ├── product_manager.py
│   │   ├── technical_architect.py
│   │   ├── frontend_builder.py
│   │   ├── backend_builder.py
│   │   ├── database_agent.py
│   │   ├── qa_testing.py
│   │   └── code_quality.py
│   └── orchestrator.py            # WorkflowOrchestrator (parallel FE+BE)
└── tests/
    └── test_base_agent.py         # pytest unit tests
```

---

## Quick Start

```bash
pip install anthropic pytest playwright
playwright install chromium

# Run tests
pytest tests/test_base_agent.py -v

# Run full pipeline
python -c "
from agents.orchestrator import WorkflowOrchestrator
result = WorkflowOrchestrator().run('Build a todo app with user authentication')
print(result['code_review'])
"
```

---

## Key Best Practices (Anthropic Docs)

- **Adaptive thinking** over manual budget — let the model decide reasoning depth
- - **tool_choice: auto** when thinking is enabled — never `type: tool`
  - - **Prompt caching** on system prompts and tool definitions — ~10x cost reduction on cache hits
    - - **Parallel subagents** for independent tasks — FE and BE builders run concurrently
      - - **Context reset** between tasks — prevents token bloat and prompt leakage
        - - **HandoffArtifact** for structured inter-agent communication
          - - **Sprint contracts** — frontend declares API needs before backend builds
            - - **QA retry loop** — automatic re-run on test failure, up to `qa_retries` attempts
             
              - ---

              ## References

              - [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
              - - [Anthropic: Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)
                - - [Claude Extended Thinking Docs](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)
