"""
Base Agent — Claude Opus 4.6 Best Practices (v4)

Key fixes applied based on current Anthropic docs:
  1. Adaptive thinking  — Opus/Sonnet 4.6 use thinking:{type:"adaptive"} + effort param.
       The old {type:"enabled", budget_tokens} + interleaved beta header are deprecated on 4.6.
         2. tool_choice conflict — thinking is INCOMPATIBLE with tool_choice:{type:"tool"}.
              Structured outputs now use tool_choice:{type:"auto"} and prompt-guided calling.
                3. Prompt caching     — system prompt and tools get cache_control:{type:"ephemeral"}
                     to cut costs on repeated calls within a session.
                       4. EffortLevel restored — maps to the effort param that controls adaptive thinking depth.
                         5. Thinking block guard — run() passes full content back (incl. thinking blocks) unchanged.
                         """

import os, json, uuid, logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Type
from pathlib import Path
from enum import Enum

import anthropic
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums & Config
# ---------------------------------------------------------------------------

class AgentType(str, Enum):
      PRODUCT_MANAGER      = "product_manager"
      TECHNICAL_ARCHITECT  = "technical_architect"
      AI_SPECIALIST        = "ai_specialist"
      FRONTEND_BUILDER     = "frontend_builder"
      BACKEND_BUILDER      = "backend_builder"
      DATABASE_AGENT       = "database_agent"
      QA_TESTING           = "qa_testing"
      CODE_QUALITY         = "code_quality"


class EffortLevel(str, Enum):
      """
          Maps to the Anthropic 'effort' parameter for adaptive thinking on Opus/Sonnet 4.6.
              Controls how deeply the model thinks before responding.
                  """
      LOW    = "low"
      MEDIUM = "medium"
      HIGH   = "high"


class AgentConfig(BaseModel):
      agent_type:       AgentType
      model:            str          = "claude-opus-4-6"
      max_tokens:       int          = 8192
      thinking_enabled: bool         = True
      effort:           EffortLevel  = EffortLevel.HIGH   # adaptive thinking depth
    tools:            List[Dict[str, Any]] = Field(default_factory=list)
    system_prompt:    Optional[str] = None
    # Context-reset threshold: reset when input tokens exceed this fraction of
    # the model's context window (200k for Opus 4.6). Set to 0 to disable.
    context_reset_threshold: float = 0.75
    # Enable prompt caching on system prompt + tool definitions
    enable_caching:   bool = True


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
      agent_id:   str
      agent_type: AgentType
      task_id:    str
      status:     str = "in_progress"
      progress:   Dict[str, Any] = Field(default_factory=dict)
      outputs:    Dict[str, str] = Field(default_factory=dict)
      errors:     List[str]      = Field(default_factory=list)
      created_at: datetime       = Field(default_factory=datetime.now)
      updated_at: datetime       = Field(default_factory=datetime.now)

    def save(self, directory: Path = Path("./agent_states")) -> None:
              directory.mkdir(parents=True, exist_ok=True)
              fp = directory / f"{self.agent_id}_{self.task_id}.json"
              fp.write_text(json.dumps(self.model_dump(mode="json"), indent=2, default=str))
              logger.info(f"State saved -> {fp}")

    @classmethod
    def load(cls, agent_id: str, task_id: str,
                          directory: Path = Path("./agent_states")) -> Optional["AgentState"]:
                                    fp = directory / f"{agent_id}_{task_id}.json"
                                    if not fp.exists():
                                                  return None
                                              return cls(**json.loads(fp.read_text()))


# ---------------------------------------------------------------------------
# Handoff artifact (context-reset support)
# ---------------------------------------------------------------------------

class HandoffArtifact(BaseModel):
      """Structured artifact passed to a fresh agent after a context reset."""
    task_id:         str
    agent_type:      str
    original_task:   str
    work_completed:  List[str] = Field(default_factory=list)
    next_steps:      List[str] = Field(default_factory=list)
    key_decisions:   List[str] = Field(default_factory=list)
    partial_outputs: Dict[str, str] = Field(default_factory=dict)
    reset_count:     int = 0

    def to_prompt(self) -> str:
              return f"""
              <context_handoff>
                <reset_count>{self.reset_count}</reset_count>
                  <original_task>{self.original_task}</original_task>
                    <work_completed>
                    {chr(10).join(f'    - {item}' for item in self.work_completed)}
                      </work_completed>
                        <next_steps>
                        {chr(10).join(f'    - {step}' for step in self.next_steps)}
                          </next_steps>
                            <key_decisions>
                            {chr(10).join(f'    - {d}' for d in self.key_decisions)}
                              </key_decisions>
                              </context_handoff>

                              Continue the task from where the previous agent left off.
                              Focus on the next_steps listed above.
                              """


# ---------------------------------------------------------------------------
# Base Agent
# ---------------------------------------------------------------------------

MODEL_CONTEXT_WINDOW = 200_000   # Claude Opus 4.6 context window
# Anthropic SDK streaming is required when max_tokens > this value to avoid timeouts.
STREAMING_THRESHOLD = 21_333


class BaseAgent:
      """
          Base class for all agents — Claude Opus 4.6 best practices.

              Thinking strategy
                  -----------------
                      For Opus 4.6 and Sonnet 4.6, Anthropic recommends adaptive thinking:
                              thinking = {"type": "adaptive"}
                                      output_config = {"effort": "<low|medium|high>"}
                                          No beta header is needed; interleaved thinking is automatic.

                                              The old manual mode (type:"enabled", budget_tokens, interleaved beta header)
                                                  is still accepted by the API but is deprecated and will be removed.

                                                      Structured outputs
                                                          ------------------
                                                              thinking is INCOMPATIBLE with tool_choice:{type:"tool"} (forced tool call).
                                                                  When thinking_enabled=True we use tool_choice:{type:"auto"} and instruct the
                                                                      model via the prompt to call the structured_output tool.
                                                                          When thinking_enabled=False we can safely use tool_choice:{type:"tool"}.

                                                                              Prompt caching
                                                                                  --------------
                                                                                      System prompt and tool definitions are marked with cache_control to reduce
                                                                                          token costs on repeated calls within a session (up to ~50% cost reduction
                                                                                              on long agentic runs).
                                                                                                  """

    CONTEXT_AWARENESS = """
    <context_management>
      Your context window is automatically managed via compaction.
        Do NOT stop tasks early due to token concerns.
          Save progress frequently before any context reset.
            Assume you can work indefinitely from where you left off.
            </context_management>
            """

    def __init__(self, config: AgentConfig, agent_id: Optional[str] = None):
              self.config      = config
        self.agent_id    = agent_id or str(uuid.uuid4())[:8]
        self.client      = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.state:      Optional[AgentState] = None
        self.outputs_dir = Path("./agent_outputs")
        self.outputs_dir.mkdir(exist_ok=True)

        # Cost tracking
        self.total_input_tokens  = 0
        self.total_output_tokens = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _system_blocks(self) -> List[Dict]:
              """
                      Return system prompt as a list of content blocks.
                              When caching is enabled the last block gets cache_control so the
                                      entire system prompt is cached by the Anthropic CDN.
                                              """
        text = (self.config.system_prompt or "") + "\n" + self.CONTEXT_AWARENESS
        block: Dict[str, Any] = {"type": "text", "text": text}
        if self.config.enable_caching:
                      block["cache_control"] = {"type": "ephemeral"}
        return [block]

    def _build_structured_output_tool(self, schema: Type[BaseModel]) -> tuple:
              """
                      Return (tool_def, tool_choice) for structured outputs.

                              IMPORTANT: when thinking is enabled, tool_choice must be "auto"
        (not "tool") because forced tool use is incompatible with thinking.
                The system prompt instructs the model to call the tool; it will do so
                        reliably without forcing.

                                When thinking is disabled, we can safely force with tool_choice "tool".
                                        """
        tool_def: Dict[str, Any] = {
                      "name": "structured_output",
                      "description": (
                                        "You MUST call this tool to return your structured response. "
                                        "Fill every field according to the schema."
                      ),
                      "input_schema": schema.model_json_schema(),
        }
        if self.config.enable_caching:
                      tool_def["cache_control"] = {"type": "ephemeral"}

        if self.config.thinking_enabled:
                      # Cannot force tool use alongside thinking — use auto
                      tool_choice = {"type": "auto"}
else:
            # Safe to force the tool call when thinking is off
              tool_choice = {"type": "tool", "name": "structured_output"}

        return tool_def, tool_choice

    def _should_reset_context(self, input_tokens: int) -> bool:
              """Return True when input tokens exceed the configured threshold."""
        if self.config.context_reset_threshold <= 0:
                      return False
        threshold = int(MODEL_CONTEXT_WINDOW * self.config.context_reset_threshold)
        return input_tokens >= threshold

    def _call(
              self,
              messages:      List[Dict],
              output_schema: Optional[Type[BaseModel]] = None,
              tools:         Optional[List[Dict]] = None,
    ) -> Dict:
              """
                      Call the Anthropic Messages API with current best-practice parameters.

                              Adaptive thinking (Opus/Sonnet 4.6):
                                          thinking = {"type": "adaptive"}
                                                      output_config = {"effort": "<effort_level>"}
                                                                  NO beta header required.

                                                                          Structured outputs:
                                                                                      Use tool_choice "auto" when thinking is on (incompatibility constraint).
                                                                                                  Use tool_choice "tool" when thinking is off.

                                                                                                          Prompt caching:
                                                                                                                      System prompt blocks and tool definitions include cache_control
                                                                                                                                  so they are served from cache on repeated calls.
                                                                                                                                          """
        kwargs: Dict[str, Any] = {
                      "model":      self.config.model,
                      "max_tokens": self.config.max_tokens,
                      "system":     self._system_blocks(),
                      "messages":   messages,
        }

        # ── Adaptive thinking (Opus/Sonnet 4.6 recommended API) ─────────
        if self.config.thinking_enabled:
                      kwargs["thinking"]      = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": self.config.effort.value}

        # ── Tool definitions ─────────────────────────────────────────────
        effective_tools:  List[Dict] = list(tools or [])
        effective_choice: Optional[Dict] = None

        if output_schema:
                      schema_tool, schema_choice = self._build_structured_output_tool(output_schema)
            effective_tools  = [schema_tool]   # schema tool takes priority
            effective_choice = schema_choice

        if effective_tools:
                      # Apply caching to external (non-schema) tools if not already marked
                      cached_tools = []
            for i, t in enumerate(effective_tools):
                              t_copy = dict(t)
                if self.config.enable_caching and "cache_control" not in t_copy:
                                      # Only the last tool gets cache_control (Anthropic requirement)
                                      if i == len(effective_tools) - 1:
                                                                t_copy["cache_control"] = {"type": "ephemeral"}
                                                        cached_tools.append(t_copy)

            kwargs["tools"] = cached_tools
            if effective_choice:
                              kwargs["tool_choice"] = effective_choice

        # ── Warn if approaching streaming threshold ───────────────────────
        if self.config.max_tokens > STREAMING_THRESHOLD:
                      logger.warning(
                                        f"max_tokens={self.config.max_tokens} exceeds the SDK streaming "
                                        f"threshold ({STREAMING_THRESHOLD}). Consider using streaming mode "
                                        "to avoid HTTP timeouts on long-running requests."
                      )

        resp = self.client.messages.create(**kwargs)

        # ── Token tracking ───────────────────────────────────────────────
        self.total_input_tokens  += resp.usage.input_tokens
        self.total_output_tokens += resp.usage.output_tokens
        logger.info(
                      f"[{self.config.agent_type}] tokens — "
                      f"in:{resp.usage.input_tokens} out:{resp.usage.output_tokens} | "
                      f"session totals in:{self.total_input_tokens} out:{self.total_output_tokens}"
        )

        return {
                      "content":     resp.content,
                      "stop_reason": resp.stop_reason,
                      "usage":       resp.usage,
        }

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save_file(self, filename: str, content: str) -> str:
              fp = self.outputs_dir / filename
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        logger.info(f"File saved -> {fp}")
        return str(fp)

    # ------------------------------------------------------------------
    # Handoff / context reset
    # ------------------------------------------------------------------

    def build_handoff(
              self,
              original_task:   str,
              work_completed:  List[str],
              next_steps:      List[str],
              key_decisions:   List[str],
              partial_outputs: Dict[str, str],
              reset_count:     int = 0,
    ) -> HandoffArtifact:
              """Construct a structured handoff artifact for a context reset."""
        artifact = HandoffArtifact(
                      task_id         = self.state.task_id if self.state else "unknown",
                      agent_type      = self.config.agent_type.value,
                      original_task   = original_task,
                      work_completed  = work_completed,
                      next_steps      = next_steps,
                      key_decisions   = key_decisions,
                      partial_outputs = partial_outputs,
                      reset_count     = reset_count,
        )
        path = f"handoff_{self.agent_id}_{artifact.task_id}_{reset_count}.json"
        self.save_file(path, artifact.model_dump_json(indent=2))
        return artifact

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    def run(
              self,
              task:           str,
              task_id:        str,
              output_schema:  Optional[Type[BaseModel]] = None,
              tools:          Optional[Dict[str, Any]]  = None,
              max_iterations: int = 15,
              handoff:        Optional[HandoffArtifact] = None,
    ) -> Any:
              """
                      Execute the agent loop.

                              Context-reset: if _should_reset_context() triggers, returns a
                                      HandoffArtifact so the caller can spin up a fresh agent.

                                              Thinking block preservation: resp["content"] is passed back
                                                      UNCHANGED into the messages list. This is required by Anthropic:
                                                              thinking blocks from the last assistant turn must be included
                                                                      unmodified when submitting tool results to maintain reasoning
                                                                              continuity. Do NOT strip or modify content blocks before
                                                                                      appending them to messages.
                                                                                              """
        # ── Init / resume state ──────────────────────────────────────────
        self.state = AgentState.load(self.agent_id, task_id) or AgentState(
                      agent_id   = self.agent_id,
                      agent_type = self.config.agent_type,
                      task_id    = task_id,
        )

        effective_task = (handoff.to_prompt() + "\n\n" + task) if handoff else task
        messages = [{"role": "user", "content": effective_task}]

        tool_defs = list(tools.values()) if tools else None

        for i in range(1, max_iterations + 1):
                      logger.info(f"[{self.config.agent_type}] iteration {i}/{max_iterations}")
            resp = self._call(messages, output_schema, tool_defs)

            # ── Context-reset check ──────────────────────────────────────
            if self._should_reset_context(resp["usage"].input_tokens):
                              logger.warning(
                                                    f"[{self.config.agent_type}] Context threshold reached at "
                                                    f"iteration {i}. Generating handoff artifact."
                              )
                reset_count = (handoff.reset_count + 1) if handoff else 1
                artifact = self.build_handoff(
                                      original_task   = task,
                                      work_completed  = [f"Completed {i} iterations"],
                                      next_steps      = ["Continue from last response"],
                                      key_decisions   = [],
                                      partial_outputs = {},
                                      reset_count     = reset_count,
                )
                self.state.status = "context_reset"
                self.state.save()
                return artifact

            # ── End turn ─────────────────────────────────────────────────
            if resp["stop_reason"] == "end_turn":
                              for block in resp["content"]:
                                                    if hasattr(block, "text"):
                                                                              text = block.text
                                                                              if output_schema:
                                                                                                            try:
                                                                                                                                              parsed = json.loads(text)
                                                                                                                                              self.state.status = "completed"
                                                                                                                                              self.state.save()
                                                                                                                                              return output_schema(**parsed)
                                                                                except Exception:
                                                                                      pass
                                                                                                  self.state.status = "completed"
                                                                                                  self.state.save()
                                                                                                  return resp["content"][-1].text if resp["content"] else ""

                                                                  # ── Tool use ─────────────────────────────────────────────────
                                                                  if resp["stop_reason"] == "tool_use":
                                                                                    # CRITICAL: append the FULL content list unchanged.
                                                                                    # Thinking blocks MUST be preserved for reasoning continuity.
                                                                                    # Do not filter or modify resp["content"] before appending.
                                                                                    messages.append({"role": "assistant", "content": resp["content"]})
                                                                                    results = []

                for block in resp["content"]:
                                      if not (hasattr(block, "type") and block.type == "tool_use"):
                                                                continue

                    # Structured output tool
                    if block.name == "structured_output" and output_schema:
                                              try:
                                                                            parsed = output_schema(**block.input)
                                                                            self.state.status = "completed"
                                                                            self.state.save()
                                                                            return parsed
except Exception as e:
                            results.append({
                                                              "type":        "tool_result",
                                                              "tool_use_id": block.id,
                                                              "content":     json.dumps({"error": str(e)}),
                            })
                        continue

                    # External caller-supplied tools
                    if tools:
                                              fn = tools.get(block.name)
                        try:
                                                      result = fn(**block.input) if fn else {"error": f"Unknown tool {block.name}"}
except Exception as e:
                            result = {"error": str(e)}
                        results.append({
                                                      "type":        "tool_result",
                                                      "tool_use_id": block.id,
                                                      "content":     json.dumps(result),
                        })

                if results:
                                      messages.append({"role": "user", "content": results})

        self.state.status = "failed"
        self.state.save()
        return None

    # ------------------------------------------------------------------
    # Cost helpers
    # ------------------------------------------------------------------

    def get_cost_summary(self) -> Dict[str, Any]:
              """Return token usage for this agent session."""
        return {
                      "agent_type":    self.config.agent_type.value,
                      "agent_id":      self.agent_id,
                      "input_tokens":  self.total_input_tokens,
                      "output_tokens": self.total_output_tokens,
                      "total_tokens":  self.total_input_tokens + self.total_output_tokens,
        }
