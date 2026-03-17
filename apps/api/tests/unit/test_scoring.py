"""Unit tests for recommendation scoring logic."""
import pytest
from app.services.scoring import compute_priority, score_recommendation, CATEGORY_MULTIPLIERS


class TestComputePriority:
    def test_perfect_recommendation_scores_near_1(self):
        result = compute_priority(
            impact=1.0, effort=0.0, confidence=1.0,
            urgency=1.0, evidence_count=5, category="technical_seo"
        )
        assert result.priority_score >= 0.95

    def test_zero_confidence_lowers_score(self):
        high_conf = compute_priority(1.0, 0.1, 1.0, 1.0, 5, "technical_seo")
        low_conf = compute_priority(1.0, 0.1, 0.0, 1.0, 5, "technical_seo")
        assert high_conf.priority_score > low_conf.priority_score

    def test_high_effort_lowers_score(self):
        low_effort = compute_priority(0.8, 0.1, 0.9, 0.8, 3, "technical_seo")
        high_effort = compute_priority(0.8, 0.9, 0.9, 0.8, 3, "technical_seo")
        assert low_effort.priority_score > high_effort.priority_score

    def test_geo_aeo_category_gets_discount(self):
        seo = compute_priority(0.8, 0.3, 0.8, 0.7, 3, "technical_seo")
        geo = compute_priority(0.8, 0.3, 0.8, 0.7, 3, "geo_aeo")
        assert seo.priority_score > geo.priority_score

    def test_score_is_capped_at_1(self):
        result = compute_priority(1.0, 0.0, 1.0, 1.0, 10, "technical_seo")
        assert result.priority_score <= 1.0

    def test_score_is_non_negative(self):
        result = compute_priority(0.0, 1.0, 0.0, 0.0, 0, "geo_aeo")
        assert result.priority_score >= 0.0

    def test_breakdown_contains_all_components(self):
        result = compute_priority(0.7, 0.3, 0.8, 0.6, 2, "on_page_seo")
        assert "impact" in result.breakdown
        assert "effort_inverse" in result.breakdown
        assert "confidence" in result.breakdown
        assert "urgency" in result.breakdown
        assert "evidence" in result.breakdown
        assert "category_multiplier" in result.breakdown

    def test_explanation_is_non_empty(self):
        result = compute_priority(0.7, 0.3, 0.8, 0.6, 2, "on_page_seo")
        assert len(result.explanation) > 20
        assert "Priority" in result.explanation

    def test_evidence_capped_at_5(self):
        result_5 = compute_priority(0.7, 0.3, 0.8, 0.6, 5, "technical_seo")
        result_50 = compute_priority(0.7, 0.3, 0.8, 0.6, 50, "technical_seo")
        assert result_5.priority_score == result_50.priority_score

    def test_no_evidence_gets_lower_score(self):
        with_evidence = compute_priority(0.7, 0.3, 0.8, 0.6, 3, "technical_seo")
        no_evidence = compute_priority(0.7, 0.3, 0.8, 0.6, 0, "technical_seo")
        assert with_evidence.priority_score > no_evidence.priority_score

    def test_all_category_multipliers_are_valid(self):
        for cat, mult in CATEGORY_MULTIPLIERS.items():
            assert 0.0 < mult <= 1.0, f"Invalid multiplier for {cat}: {mult}"


class TestScoreRecommendation:
    def test_convenience_wrapper_works(self):
        evidence = [{"type": "crawl", "finding": "Missing title"}]
        result = score_recommendation(0.8, 0.2, 0.9, 0.7, evidence, "technical_seo")
        assert 0.0 <= result.priority_score <= 1.0
        assert result.breakdown is not None
