"""Unit tests for PolicyGateAgent."""
import pytest
from app.agents.layer0.policy_gate import PolicyGateAgent, PolicyCheckInput
from app.agents.base import AgentRunContext


class TestPolicyGateAgent:
    @pytest.mark.asyncio
    async def test_blocks_prohibited_actions(self):
        agent = PolicyGateAgent()
        ctx = AgentRunContext(autonomy_level=4)
        result = await agent.run(
            PolicyCheckInput(action_type="send_spam", action_description="Mass email"),
            ctx,
        )
        assert result.success
        assert result.output.allowed is False
        assert "PROHIBITED" in result.output.policy_flags[0]

    @pytest.mark.asyncio
    async def test_blocks_insufficient_autonomy(self):
        agent = PolicyGateAgent()
        ctx = AgentRunContext(autonomy_level=1)
        result = await agent.run(
            PolicyCheckInput(action_type="publish_content", action_description="Publish blog"),
            ctx,
        )
        assert result.success
        assert result.output.allowed is False
        assert result.output.required_autonomy_level == 4

    @pytest.mark.asyncio
    async def test_allows_analysis_at_level_0(self):
        agent = PolicyGateAgent()
        ctx = AgentRunContext(autonomy_level=0)
        result = await agent.run(
            PolicyCheckInput(action_type="analyze_site", action_description="SEO audit"),
            ctx,
        )
        assert result.success
        assert result.output.allowed is True

    @pytest.mark.asyncio
    async def test_allows_draft_at_level_1(self):
        agent = PolicyGateAgent()
        ctx = AgentRunContext(autonomy_level=1)
        result = await agent.run(
            PolicyCheckInput(action_type="generate_content_draft", action_description="Blog draft"),
            ctx,
        )
        assert result.success
        assert result.output.allowed is True

    @pytest.mark.asyncio
    async def test_approval_required_below_level_3(self):
        agent = PolicyGateAgent()
        ctx = AgentRunContext(autonomy_level=1)
        result = await agent.run(
            PolicyCheckInput(action_type="generate_report", action_description="Weekly report"),
            ctx,
        )
        assert result.success
        assert result.output.allowed is True
        assert result.output.approval_required is True

    @pytest.mark.asyncio
    async def test_fake_review_is_prohibited(self):
        agent = PolicyGateAgent()
        ctx = AgentRunContext(autonomy_level=4)
        result = await agent.run(
            PolicyCheckInput(action_type="generate_fake_review", action_description="Fake testimonial"),
            ctx,
        )
        assert result.success
        assert result.output.allowed is False


class TestComplianceGuardian:
    @pytest.mark.asyncio
    async def test_flags_deceptive_guarantee(self):
        from app.agents.layer0.compliance import ComplianceGuardianAgent, ComplianceInput
        agent = ComplianceGuardianAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            ComplianceInput(
                content="Our product is guaranteed to triple your revenue with zero risk!",
                content_type="landing_page",
                channel="owned",
            ),
            ctx,
        )
        assert result.success
        flag_types = [f.flag_type for f in result.output.flags]
        assert "deceptive_language" in flag_types

    @pytest.mark.asyncio
    async def test_community_channel_requires_review(self):
        from app.agents.layer0.compliance import ComplianceGuardianAgent, ComplianceInput
        agent = ComplianceGuardianAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            ComplianceInput(
                content="Check out our product!",
                content_type="social_post",
                channel="reddit",
            ),
            ctx,
        )
        assert result.success
        assert result.output.safe_to_auto_publish is False
        flag_types = [f.flag_type for f in result.output.flags]
        assert "channel_requires_review" in flag_types

    @pytest.mark.asyncio
    async def test_clean_content_passes(self):
        from app.agents.layer0.compliance import ComplianceGuardianAgent, ComplianceInput
        agent = ComplianceGuardianAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            ComplianceInput(
                content="We help engineering teams track sprint progress with clear dashboards.",
                content_type="landing_page",
                channel="owned",
            ),
            ctx,
        )
        assert result.success
        assert result.output.passed is True
        assert result.output.risk_score < 0.3
