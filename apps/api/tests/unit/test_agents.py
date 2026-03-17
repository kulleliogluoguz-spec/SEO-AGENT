"""Unit tests for agent base class and infrastructure."""
import uuid
from typing import ClassVar

import pytest
from pydantic import BaseModel

from app.agents.base import (
    AgentMetadata,
    AgentRunContext,
    AgentResult,
    BaseAgent,
    LLMAgent,
)


# ─── Test Agents ──────────────────────────────────────────────────────────────

class SimpleInput(BaseModel):
    value: str


class SimpleOutput(BaseModel):
    result: str
    processed: bool = True


class SucceedingAgent(BaseAgent[SimpleInput, SimpleOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="SucceedingAgent",
        layer=0,
        description="Test agent that always succeeds",
        requires_llm=False,
    )

    async def _execute(self, input_data: SimpleInput, context: AgentRunContext) -> SimpleOutput:
        return SimpleOutput(result=f"processed:{input_data.value}")


class FailingAgent(BaseAgent[SimpleInput, SimpleOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="FailingAgent",
        layer=0,
        description="Test agent that always fails",
        requires_llm=False,
    )

    async def _execute(self, input_data: SimpleInput, context: AgentRunContext) -> SimpleOutput:
        raise ValueError("Intentional test failure")


class HighAutonomyAgent(BaseAgent[SimpleInput, SimpleOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="HighAutonomyAgent",
        layer=0,
        description="Requires autonomy level 4",
        requires_llm=False,
        autonomy_min_level=4,
    )

    async def _execute(self, input_data: SimpleInput, context: AgentRunContext) -> SimpleOutput:
        return SimpleOutput(result="executed")


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        agent = SucceedingAgent()
        result = await agent.run(SimpleInput(value="hello"))
        assert result.success is True
        assert result.output is not None
        assert result.output.result == "processed:hello"
        assert result.agent_name == "SucceedingAgent"

    @pytest.mark.asyncio
    async def test_failed_execution_returns_error(self):
        agent = FailingAgent()
        result = await agent.run(SimpleInput(value="test"))
        assert result.success is False
        assert result.error == "Intentional test failure"
        assert result.output is None

    @pytest.mark.asyncio
    async def test_dry_run_returns_success_without_executing(self):
        agent = FailingAgent()
        ctx = AgentRunContext(dry_run=True)
        result = await agent.run(SimpleInput(value="test"), ctx)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_autonomy_gate_blocks_insufficient_level(self):
        agent = HighAutonomyAgent()
        ctx = AgentRunContext(autonomy_level=1)
        result = await agent.run(SimpleInput(value="test"), ctx)
        assert result.success is False
        assert "autonomy" in result.error.lower()

    @pytest.mark.asyncio
    async def test_autonomy_gate_allows_sufficient_level(self):
        agent = HighAutonomyAgent()
        ctx = AgentRunContext(autonomy_level=4)
        result = await agent.run(SimpleInput(value="test"), ctx)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_duration_is_tracked(self):
        agent = SucceedingAgent()
        result = await agent.run(SimpleInput(value="test"))
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_trace_id_is_set(self):
        agent = SucceedingAgent()
        ctx = AgentRunContext(trace_id="test-trace-001")
        result = await agent.run(SimpleInput(value="test"), ctx)
        assert result.trace_id == "test-trace-001"

    @pytest.mark.asyncio
    async def test_context_defaults_are_safe(self):
        agent = SucceedingAgent()
        ctx = AgentRunContext()
        assert ctx.autonomy_level == 1
        assert ctx.demo_mode is False
        assert ctx.dry_run is False


class TestAgentRegistry:
    def test_all_agents_registered(self):
        from app.agents.registry import AGENT_REGISTRY
        assert len(AGENT_REGISTRY) == 138

    def test_agent_lookup_by_name(self):
        from app.agents.registry import get_agent
        agent = get_agent("TechnicalSEOAuditAgent")
        assert agent is not None
        assert agent.layer == 4

    def test_agents_by_layer(self):
        from app.agents.registry import get_agents_for_layer
        layer4 = get_agents_for_layer(4)
        assert len(layer4) > 0
        assert all(a.layer == 4 for a in layer4)

    def test_nonexistent_agent_returns_none(self):
        from app.agents.registry import get_agent
        assert get_agent("NonExistentAgent") is None

    def test_agent_names_are_unique(self):
        from app.agents.registry import AGENT_REGISTRY
        names = [a.name for a in AGENT_REGISTRY]
        assert len(names) == len(set(names)), "Duplicate agent names found"

    def test_all_agents_have_module_path(self):
        from app.agents.registry import AGENT_REGISTRY
        for agent in AGENT_REGISTRY:
            assert agent.module_path, f"{agent.name} has no module_path"
