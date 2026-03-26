"""
Base Agent — Claude 4.6 Best Practices
Adaptive thinking · Structured outputs · State persistence · Strict tool use
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
class AgentType(str, Enum):
    PRODUCT_MANAGER     = "product_manager"
    TECHNICAL_ARCHITECT = "technical_architect"
    AI_SPECIALIST       = "ai_specialist"
    FRONTEND_BUILDER    = "frontend_builder"
    BACKEND_BUILDER     = "backend_builder"
    DATABASE_AGENT      = "database_agent"
    QA_TESTING          = "qa_testing"
    CODE_QUALITY        = "code_quality"
class EffortLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
class AgentConfig(BaseModel):
    agent_type:       AgentType
    model:            str         = "claude-opus-4-6"
    max_tokens:       int         = 8192
    effort:           EffortLevel = EffortLevel.HIGH
    thinking_enabled: bool        = True
    tools:            List[Dict[str, Any]] = Field(default_factory=list)
    system_prompt:    Optional[str] = None
class AgentState(BaseModel):
    agent_id:   str
    agent_type: AgentType
    task_id:    str
    status:     str = "in_progress"
    progress:   Dict[str, Any]  = Field(default_factory=dict)
    outputs:    Dict[str, str]  = Field(default_factory=dict)
    errors:     List[str]       = Field(default_factory=list)
    created_at: datetime        = Field(default_factory=datetime.now)
    updated_at: datetime        = Field(default_factory=datetime.now)
    def save(self, directory: Path = Path("./agent_states")):
        directory.mkdir(parents=True, exist_ok=True)
        fp = directory / f"{self.agent_id}_{self.task_id}.json"
        fp.write_text(json.dumps(self.model_dump(mode="json"), indent=2, default=str))
        logger.info(f"State saved → {fp}")
    @classmethod
    def load(cls, agent_id: str, task_id: str, directory: Path = Path("./agent_states")):
        fp = directory / f"{agent_id}_{task_id}.json"
        if not fp.exists():
            return None
        return cls(**json.loads(fp.read_text()))
class BaseAgent:
    """Base class for all agents — Claude 4.6 best practices built in."""
    CONTEXT_AWARENESS = """
<context_management>
Your context window is automatically managed. Do NOT stop tasks early due to token concerns.
Save progress frequently using the save_state tool before context resets.
Assume you can work indefinitely from where you left off.
</context_management>
"""
    def __init__(self, config: AgentConfig, agent_id: Optional[str] = None):
        self.config     = config
        self.agent_id   = agent_id or str(uuid.uuid4())[:8]
        self.client     = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.state: Optional[AgentState] = None
        self.outputs_dir = Path("./agent_outputs")
        self.outputs_dir.mkdir(exist_ok=True)
    def _system(self) -> str:
        base = self.config.system_prompt or ""
        return f"{base}\\n{self.CONTEXT_AWARENESS}"
    def _thinking(self) -> Optional[Dict]:
        return {"type": "adaptive"} if self.config.thinking_enabled else None
    def _call(
        self,
        messages: List[Dict],
        output_schema: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Dict:
        kwargs: Dict[str, Any] = {
            "model":      self.config.model,
            "max_tokens": self.config.max_tokens,
            "system":     self._system(),
            "messages":   messages,
        }
        if self.config.thinking_enabled:
            kwargs["thinking"]      = self._thinking()
            kwargs["output_config"] = {"effort": self.config.effort.value}
        if output_schema:
            kwargs.setdefault("output_config", {})["format"] = {
                "type":   "json_schema",
                "schema": output_schema.model_json_schema(),
            }
        if tools:
            for t in tools:
                t["strict"] = True
            kwargs["tools"] = tools
        resp = self.client.messages.create(**kwargs)
        logger.info(f"Tokens — in:{resp.usage.input_tokens} out:{resp.usage.output_tokens}")
        return {"content": resp.content, "stop_reason": resp.stop_reason, "usage": resp.usage}
    def save_file(self, filename: str, content: str) -> str:
        fp = self.outputs_dir / filename
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        logger.info(f"File saved → {fp}")
        return str(fp)
    def run(
        self,
        task: str,
        task_id: str,
        output_schema: Optional[Type[BaseModel]] = None,
        tools: Optional[Dict[str, Any]] = None,
        max_iterations: int = 15,
    ) -> Any:
        # init state
        self.state = AgentState.load(self.agent_id, task_id) or AgentState(
            agent_id=self.agent_id, agent_type=self.config.agent_type, task_id=task_id
        )
        messages = [{"role": "user", "content": task}]
        tool_defs = list(tools.values()) if tools else None
        for i in range(1, max_iterations + 1):
            logger.info(f"Iteration {i}/{max_iterations}")
            resp = self._call(messages, output_schema, tool_defs)
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
                        return text
                return resp["content"]
            if resp["stop_reason"] == "tool_use" and tools:
                messages.append({"role": "assistant", "content": resp["content"]})
                results = []
                for block in resp["content"]:
                    if hasattr(block, "type") and block.type == "tool_use":
                        fn = tools.get(block.name)
                        try:
                            result = fn(**block.input) if fn else {"error": f"Unknown tool {block.name}"}
                        except Exception as e:
                            result = {"error": str(e)}
                        results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
                messages.append({"role": "user", "content": results})
        self.state.status = "failed"
        self.state.save()
        return None
