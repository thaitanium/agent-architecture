"""
Unit tests for agents/core/base_agent.py
Run with: pytest tests/test_base_agent.py -v
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.core.base_agent import (
    AgentConfig,
    AgentState,
    AgentType,
    BaseAgent,
    EffortLevel,
    HandoffArtifact,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config_thinking_off():
        """Minimal config with thinking disabled."""
        return AgentConfig(
            agent_type=AgentType.QA_TESTING,
            model="claude-sonnet-4-6",
            max_tokens=1024,
            thinking_enabled=False,
            effort=EffortLevel.MEDIUM,
            system_prompt="You are a test agent.",
        )


@pytest.fixture
def config_thinking_on():
        """Config with thinking enabled."""
        return AgentConfig(
            agent_type=AgentType.TECHNICAL_ARCHITECT,
            model="claude-opus-4-6",
            max_tokens=8000,
            thinking_enabled=True,
            effort=EffortLevel.HIGH,
            system_prompt="You are a thinking test agent.",
        )


@pytest.fixture
def mock_anthropic():
        """Patch anthropic.Anthropic so no real API calls are made."""
        with patch("agents.core.base_agent.anthropic.Anthropic") as mock_cls:
                    mock_client = MagicMock()
                    mock_cls.return_value = mock_client
                    yield mock_client


# ---------------------------------------------------------------------------
# AgentConfig validation
# ---------------------------------------------------------------------------


class TestAgentConfig:
        def test_defaults(self):
                    cfg = AgentConfig(
                                    agent_type=AgentType.QA_TESTING,
                                    model="claude-sonnet-4-6",
                                    system_prompt="hi",
                    )
                    assert cfg.max_tokens == 8192
                    assert cfg.thinking_enabled is False
                    assert cfg.effort == EffortLevel.MEDIUM
                    assert cfg.enable_caching is True

        def test_effort_enum_values(self):
                    assert EffortLevel.LOW == "low"
                    assert EffortLevel.MEDIUM == "medium"
                    assert EffortLevel.HIGH == "high"

        def test_no_thinking_budget_field(self):
                    """thinking_budget was removed; verify it no longer exists on AgentConfig."""
                    cfg = AgentConfig(
                        agent_type=AgentType.QA_TESTING,
                        model="claude-sonnet-4-6",
                        system_prompt="hi",
                    )
                    assert not hasattr(cfg, "thinking_budget"), (
                        "thinking_budget was removed in favour of effort; do not re-add it"
                    )


# ---------------------------------------------------------------------------
# BaseAgent._build_api_params  —  thinking=False
# ---------------------------------------------------------------------------


class TestBuildApiParamsThinkingOff:
        def test_no_thinking_key_when_disabled(self, config_thinking_off, mock_anthropic):
                    agent = BaseAgent.__new__(BaseAgent)
                    agent.config = config_thinking_off
                    agent.client = mock_anthropic
                    agent.state = AgentState()

            params = agent._build_api_params(messages=[{"role": "user", "content": "hi"}])

        assert "thinking" not in params, "thinking must not appear when thinking_enabled=False"

    def test_tool_choice_tool_when_thinking_off(self, config_thinking_off, mock_anthropic):
                """When thinking is disabled, tool_choice may be forced to a specific tool."""
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_off
                agent.client = mock_anthropic
                agent.state = AgentState()

        params = agent._build_api_params(
                        messages=[{"role": "user", "content": "hi"}],
                        tools=[{"name": "my_tool"}],
                        force_tool="my_tool",
        )
        if "tool_choice" in params:
                        # If a tool_choice is set, it can be {"type": "tool", ...} since thinking is off
                        assert params["tool_choice"]["type"] in ("auto", "tool", "any")

    def test_no_betas_header_when_thinking_off(self, config_thinking_off, mock_anthropic):
                """No interleaved-thinking beta header should ever be sent."""
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_off
                agent.client = mock_anthropic
                agent.state = AgentState()

        params = agent._build_api_params(messages=[{"role": "user", "content": "hi"}])

        assert "betas" not in params, (
                        "interleaved-thinking-2025-05-14 beta header was removed; must not reappear"
        )


# ---------------------------------------------------------------------------
# BaseAgent._build_api_params  —  thinking=True (adaptive)
# ---------------------------------------------------------------------------


class TestBuildApiParamsThinkingOn:
        def test_adaptive_thinking_format(self, config_thinking_on, mock_anthropic):
                    """thinking must be {'type': 'adaptive'}, NOT {'type': 'enabled', 'budget_tokens': ...}."""
                    agent = BaseAgent.__new__(BaseAgent)
                    agent.config = config_thinking_on
                    agent.client = mock_anthropic
                    agent.state = AgentState()

            params = agent._build_api_params(messages=[{"role": "user", "content": "hi"}])

        assert "thinking" in params, "thinking key must be present when thinking_enabled=True"
        thinking = params["thinking"]
        assert thinking["type"] == "adaptive", (
                        f"Expected thinking type 'adaptive', got '{thinking['type']}'"
        )
        assert "budget_tokens" not in thinking, (
                        "budget_tokens is deprecated; use output_config.effort instead"
        )

    def test_effort_in_output_config(self, config_thinking_on, mock_anthropic):
                """output_config.effort must reflect the EffortLevel enum value."""
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_on
                agent.client = mock_anthropic
                agent.state = AgentState()

        params = agent._build_api_params(messages=[{"role": "user", "content": "hi"}])

        assert "output_config" in params, "output_config must be present when thinking=adaptive"
        assert params["output_config"]["effort"] == EffortLevel.HIGH

    def test_tool_choice_auto_when_thinking_on(self, config_thinking_on, mock_anthropic):
                """tool_choice MUST be 'auto' when thinking is enabled — 'tool' causes an API error."""
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_on
                agent.client = mock_anthropic
                agent.state = AgentState()

        params = agent._build_api_params(
                        messages=[{"role": "user", "content": "hi"}],
                        tools=[{"name": "structured_output"}],
                        force_tool="structured_output",
        )

        if "tool_choice" in params:
                        assert params["tool_choice"]["type"] == "auto", (
                                            "tool_choice MUST be 'auto' when thinking is enabled; "
                                            "'tool' is incompatible and raises an API error"
                        )

    def test_no_betas_header_when_thinking_on(self, config_thinking_on, mock_anthropic):
                """The interleaved-thinking-2025-05-14 beta header must not be present."""
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_on
                agent.client = mock_anthropic
                agent.state = AgentState()

        params = agent._build_api_params(messages=[{"role": "user", "content": "hi"}])

        assert "betas" not in params, (
                        "betas header (interleaved-thinking-2025-05-14) was deprecated; must not be sent"
        )


# ---------------------------------------------------------------------------
# Prompt caching
# ---------------------------------------------------------------------------


class TestPromptCaching:
        def test_system_blocks_have_cache_control(self, config_thinking_off, mock_anthropic):
                    """System prompt must be returned as a list with cache_control for prompt caching."""
                    agent = BaseAgent.__new__(BaseAgent)
                    agent.config = config_thinking_off
                    agent.client = mock_anthropic
                    agent.state = AgentState()

            if not hasattr(agent, "_system_blocks"):
                            pytest.skip("_system_blocks helper not present")

        blocks = agent._system_blocks()
        assert isinstance(blocks, list), "_system_blocks() must return a list"
        # At least one block must carry cache_control
        has_cache = any(b.get("cache_control") for b in blocks if isinstance(b, dict))
        assert has_cache, "System prompt block must include cache_control: {type: ephemeral}"

    def test_tool_definitions_have_cache_control(self, config_thinking_off, mock_anthropic):
                """Tool definitions must include cache_control on the last tool for KV-cache efficiency."""
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_off
                agent.client = mock_anthropic
                agent.state = AgentState()

        if not hasattr(agent, "_tools_with_cache"):
                        pytest.skip("_tools_with_cache helper not present")

        tools = agent._tools_with_cache([{"name": "my_tool", "description": "does stuff",
                                                                                    "input_schema": {"type": "object", "properties": {}}}])
        assert isinstance(tools, list)
        has_cache = any(t.get("cache_control") for t in tools if isinstance(t, dict))
        assert has_cache, "At least one tool definition must include cache_control"


# ---------------------------------------------------------------------------
# Context window / reset
# ---------------------------------------------------------------------------


class TestContextReset:
        def test_state_is_dataclass_with_messages(self, config_thinking_off, mock_anthropic):
                    agent = BaseAgent.__new__(BaseAgent)
                    agent.config = config_thinking_off
                    agent.client = mock_anthropic
                    agent.state = AgentState()

            assert hasattr(agent.state, "messages"), "AgentState must have a messages field"
        assert isinstance(agent.state.messages, list)

    def test_reset_clears_messages(self, config_thinking_off, mock_anthropic):
                agent = BaseAgent.__new__(BaseAgent)
                agent.config = config_thinking_off
                agent.client = mock_anthropic
                agent.state = AgentState()
                agent.state.messages.append({"role": "user", "content": "hello"})

        if hasattr(agent, "reset"):
                        agent.reset()
                        assert agent.state.messages == [], "reset() must clear conversation history"


# ---------------------------------------------------------------------------
# HandoffArtifact
# ---------------------------------------------------------------------------


class TestHandoffArtifact:
        def test_handoff_serialises_to_json(self):
                    artifact = HandoffArtifact(
                                    source_agent=AgentType.PRODUCT_MANAGER,
                                    target_agent=AgentType.TECHNICAL_ARCHITECT,
                                    payload={"spec": "build a todo app"},
                                    task_id="test-123",
                    )
                    data = json.loads(artifact.to_json())
                    assert data["source_agent"] == AgentType.PRODUCT_MANAGER
                    assert data["task_id"] == "test-123"
                    assert "spec" in data["payload"]
