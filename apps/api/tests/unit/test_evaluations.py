"""Evaluation harness regression tests."""
import pytest
from app.evaluations.harness import get_benchmark_harness


class TestEvaluationHarness:
    @pytest.mark.asyncio
    async def test_benchmark_cases_run(self):
        harness = get_benchmark_harness()
        results = await harness.run_all(demo_mode=True)
        assert results["total"] > 0
        assert "pass_rate" in results

    @pytest.mark.asyncio
    async def test_recommendation_quality_checks_evidence(self):
        """Recommendations without evidence should fail quality check."""
        import uuid
        from app.agents.layer12.rec_quality import RecommendationQualityAgent, RecommendationQualityInput
        from app.agents.base import AgentRunContext

        agent = RecommendationQualityAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            RecommendationQualityInput(
                recommendation_id=uuid.uuid4(),
                title="Fix missing title tags",
                category="technical_seo",
                summary="Pages are missing title tags",
                rationale="Title tags are important for SEO and CTR",
                evidence=[],  # No evidence!
                proposed_action="Add title tags to all pages",
                impact_score=0.8,
                effort_score=0.2,
                confidence_score=0.9,
                risk_flags=[],
            ),
            ctx,
        )
        assert result.success
        assert result.output.passed is False
        issues = [i for i in result.output.issues if "evidence" in i.lower()]
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_recommendation_quality_passes_for_complete_rec(self):
        """Well-formed recommendations should pass quality check."""
        import uuid
        from app.agents.layer12.rec_quality import RecommendationQualityAgent, RecommendationQualityInput
        from app.agents.base import AgentRunContext

        agent = RecommendationQualityAgent()
        ctx = AgentRunContext(demo_mode=True)
        result = await agent.run(
            RecommendationQualityInput(
                recommendation_id=uuid.uuid4(),
                title="Add meta description to pricing page",
                category="technical_seo",
                summary="The pricing page is missing a meta description, reducing CTR in search results.",
                rationale=(
                    "Pages without meta descriptions get auto-generated snippets which typically "
                    "have 20-30% lower CTR than pages with optimized descriptions."
                ),
                evidence=[
                    {"type": "crawl", "url": "https://example.com/pricing", "finding": "No meta description found"}
                ],
                proposed_action="Add: <meta name='description' content='Acme SaaS pricing — simple monthly plans starting at $49. Free trial available.'>",
                impact_score=0.7,
                effort_score=0.1,
                confidence_score=0.95,
                risk_flags=[],
            ),
            ctx,
        )
        assert result.success
        assert result.output.passed is True
        assert result.output.overall_score >= 0.6
