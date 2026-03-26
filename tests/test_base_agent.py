"""
Unit tests for agents/core/base_agent.py
Run with: pytest tests/test_base_agent.py -v
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agents.core.base_agent import (
    AgentConfig, AgentState, AgentType, BaseAgent, HandoffArtifact,
)


@pytest.fixture
def config():
      return AgentConfig(
                agent_type=AgentType.QA_TESTING,
                model="claude-opus-4-6",
                max_tokens=1024,
                thinking_enabled=False,
                thinking_budget=0,
                context_reset_threshold=0.75,
      )

@pytest.fixture
def agent(config):
      with patch("anthropic.Anthropic"):
                return BaseAgent(config, agent_id="test01")


class TestAgentState:
      def test_save_and_load_roundtrip(self, tmp_path):
                state = AgentState(agent_id="abc", agent_type=AgentType.PRODUCT_MANAGER, task_id="t1")
                state.save(directory=tmp_path)
                loaded = AgentState.load("abc", "t1", directory=tmp_path)
                assert loaded is not None
                assert loaded.agent_id == "abc"
                assert loaded.task_id == "t1"
                assert loaded.agent_type == AgentType.PRODUCT_MANAGER

      def test_load_missing_returns_none(self, tmp_path):
                assert AgentState.load("x", "y", directory=tmp_path) is None

      def test_save_creates_parent_dirs(self, tmp_path):
                deep = tmp_path / "a" / "b"
                state = AgentState(agent_id="x", agent_type=AgentType.CODE_QUALITY, task_id="t")
                state.save(directory=deep)
                assert deep.exists()


class TestHandoffArtifact:
      def test_to_prompt_includes_original_task(self):
                a = HandoffArtifact(
                              task_id="t", agent_type="qa_testing",
                              original_task="Build login page",
                              next_steps=["Add form validation"],
                              reset_count=1,
                )
                prompt = a.to_prompt()
                assert "Build login page" in prompt
                assert "Add form validation" in prompt

      def test_reset_count_stored(self):
                a = HandoffArtifact(task_id="t", agent_type="fe", original_task="x", reset_count=3)
                assert a.reset_count == 3


class TestStructuredOutputTool:
      def test_tool_name(self, agent):
                from pydantic import BaseModel
                class S(BaseModel):
                              v: str
                          tools, choice = agent._build_structured_output_tool(S)
                assert tools[0]["name"] == "structured_output"
                assert choice == {"type": "tool", "name": "structured_output"}

      def test_schema_properties_present(self, agent):
                from pydantic import BaseModel
                class S(BaseModel):
                              count: int
                              name: str
                          tools, _ = agent._build_structured_output_tool(S)
                props = tools[0]["input_schema"].get("properties", {})
                assert "count" in props
                assert "name" in props


class TestContextReset:
      def test_no_reset_below_threshold(self, agent):
                assert agent._should_reset_context(100_000) is False

      def test_reset_at_threshold(self, agent):
                assert agent._should_reset_context(150_000) is True

      def test_disabled_when_zero(self, config):
                config.context_reset_threshold = 0
                with patch("anthropic.Anthropic"):
                              a = BaseAgent(config)
                          assert a._should_reset_context(200_000) is False


class TestSDKParams:
      def _mock_resp(self, in_tok=100, out_tok=50):
                r = MagicMock()
                r.content = [MagicMock(type="text", text="ok")]
                r.stop_reason = "end_turn"
                r.usage.input_tokens = in_tok
                r.usage.output_tokens = out_tok
                return r

      def test_thinking_enabled_uses_correct_params(self, config):
                config.thinking_enabled = True
                config.thinking_budget = 3000
                with patch("anthropic.Anthropic") as cls:
                              client = MagicMock()
                              cls.return_value = client
                              client.messages.create.return_value = self._mock_resp()
                              a = BaseAgent(config)
                              a._call([{"role": "user", "content": "hi"}])
                          kw = client.messages.create.call_args[1]
                assert "betas" in kw
                assert "interleaved-thinking-2025-05-14" in kw["betas"]
                assert kw["thinking"]["type"] == "enabled"
                assert kw["thinking"]["budget_tokens"] == 3000

      def test_no_output_config_format(self, config):
                config.thinking_enabled = False
                with patch("anthropic.Anthropic") as cls:
                              client = MagicMock()
                              cls.return_value = client
                              client.messages.create.return_value = self._mock_resp()
                              a = BaseAgent(config)
                              a._call([{"role": "user", "content": "hi"}])
                          kw = client.messages.create.call_args[1]
                assert "output_config" not in kw

      def test_token_accumulation(self, config):
                config.thinking_enabled = False
                with patch("anthropic.Anthropic") as cls:
                              client = MagicMock()
                              cls.return_value = client
                              client.messages.create.return_value = self._mock_resp(100, 50)
                              a = BaseAgent(config)
                              a._call([{"role": "user", "content": "hi"}])
                              a._call([{"role": "user", "content": "bye"}])
                          assert a.total_input_tokens == 200
                assert a.total_output_tokens == 100


class TestRunStructuredOutput:
      def test_returns_pydantic_model_from_tool_use(self, config):
                from pydantic import BaseModel
                class Out(BaseModel):
                              result: str
                          config.thinking_enabled = False
                with patch("anthropic.Anthropic") as cls:
                              client = MagicMock()
                              cls.return_value = client
                              tb = MagicMock()
                              tb.type = "tool_use"
                              tb.name = "structured_output"
                              tb.id = "tool_1"
                              tb.input = {"result": "success"}
                              r = MagicMock()
                              r.content = [tb]
                              r.stop_reason = "tool_use"
                              r.usage.input_tokens = 100
                              r.usage.output_tokens = 50
                              client.messages.create.return_value = r
                              a = BaseAgent(config)
                              result = a.run(task="do it", task_id="t1", output_schema=Out)
                          assert isinstance(result, Out)
                assert result.result == "success"


class TestCostSummary:
      def test_keys_present(self, agent):
                s = agent.get_cost_summary()
                for k in ["agent_type", "input_tokens", "output_tokens", "total_tokens"]:
                              assert k in s

            def test_initial_zeros(self, agent):
                      s = agent.get_cost_summary()
                      assert s["input_tokens"] == 0
                      assert s["output_tokens"] == 0
                      assert s["total_tokens"] == 0
              
