"""Unit tests for the prompt registry."""
import pytest
from app.prompts.registry.prompts import (
    PROMPT_REGISTRY,
    get_prompt,
    list_prompts,
)


class TestPromptRegistry:
    def test_core_prompts_registered(self):
        prompts = list_prompts()
        assert "site_summarization" in prompts
        assert "icp_inference" in prompts
        assert "seo_recommendation" in prompts
        assert "content_brief" in prompts
        assert "report_synthesis" in prompts

    def test_get_existing_prompt(self):
        p = get_prompt("site_summarization")
        assert p.name == "site_summarization"
        assert p.family == "onboarding"

    def test_get_nonexistent_raises(self):
        with pytest.raises(KeyError):
            get_prompt("this_does_not_exist")

    def test_each_prompt_has_latest_version(self):
        for name in list_prompts():
            p = PROMPT_REGISTRY[name]
            assert p.latest is not None, f"{name} has no active version"

    def test_render_with_valid_vars(self):
        p = get_prompt("site_summarization")
        system, user = p.render(
            url="https://example.com",
            page_titles="Home, Pricing, About",
            content_sample="We help teams ship faster.",
        )
        assert "https://example.com" in user
        assert len(system) > 10

    def test_render_missing_var_raises(self):
        p = get_prompt("site_summarization")
        with pytest.raises(ValueError, match="Missing prompt variable"):
            p.render(url="https://example.com")  # missing page_titles and content_sample

    def test_prompt_has_risk_notes(self):
        """Every prompt with LLM output should document risks."""
        p = get_prompt("site_summarization")
        assert p.latest.risk_notes, "site_summarization should have risk notes"

    def test_prompt_versions_not_deprecated_by_default(self):
        p = get_prompt("content_brief")
        assert p.latest is not None
        assert not p.latest.deprecated
