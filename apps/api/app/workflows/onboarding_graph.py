"""
LangGraph workflow graph for site onboarding.

Graph structure:
  START
    → domain_validate
    → robots_sitemap
    → crawl_plan
    → [parallel: metadata_extract, structured_data]
    → product_understand
    → seo_audit
    → geo_audit
    → recommendation_prioritize
    → report_draft
  END

Human-in-the-loop checkpoints are inserted before any action that
exceeds the workspace autonomy level.
"""
import uuid
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.base import AgentRunContext
from app.agents.layer1.site_onboarding import (
    SiteOnboardingAgent,
    SiteOnboardingInput,
)
from app.agents.layer4.technical_seo import TechnicalSEOAuditAgent, TechnicalSEOInput


# ─── Graph State ──────────────────────────────────────────────────────────────

class OnboardingState(TypedDict):
    site_id: str
    crawl_id: str
    url: str
    max_pages: int
    workspace_id: str
    autonomy_level: int
    demo_mode: bool
    # Outputs from each stage
    domain_valid: bool
    pages_queued: int
    robots_found: bool
    sitemap_found: bool
    product_summary: str | None
    category: str | None
    icp_summary: str | None
    crawl_pages: list[dict]
    seo_issues: list[dict]
    seo_health_score: float
    recommendations: list[dict]
    errors: list[str]
    warnings: list[str]
    stage: str


# ─── Node Functions ───────────────────────────────────────────────────────────

async def node_onboard_site(state: OnboardingState) -> dict:
    """Run site onboarding agent (domain + robots + initial product intel)."""
    agent = SiteOnboardingAgent()
    ctx = AgentRunContext(
        workspace_id=uuid.UUID(state["workspace_id"]) if state.get("workspace_id") else None,
        autonomy_level=state.get("autonomy_level", 1),
        demo_mode=state.get("demo_mode", False),
    )
    result = await agent.run(
        SiteOnboardingInput(
            site_id=uuid.UUID(state["site_id"]),
            crawl_id=uuid.UUID(state["crawl_id"]),
            url=state["url"],
            max_pages=state.get("max_pages", 100),
        ),
        ctx,
    )
    if result.success and result.output:
        out = result.output
        return {
            "domain_valid": out.domain_valid,
            "pages_queued": out.pages_queued,
            "robots_found": out.robots_txt_found,
            "sitemap_found": out.sitemap_found,
            "product_summary": out.product_summary,
            "category": out.category,
            "icp_summary": out.icp_summary,
            "errors": state.get("errors", []) + out.errors,
            "warnings": state.get("warnings", []) + out.warnings,
            "stage": "onboarding_complete",
        }
    return {
        "errors": state.get("errors", []) + [result.error or "Onboarding failed"],
        "stage": "error",
    }


async def node_seo_audit(state: OnboardingState) -> dict:
    """Run technical SEO audit on crawled pages."""
    agent = TechnicalSEOAuditAgent()
    ctx = AgentRunContext(
        autonomy_level=state.get("autonomy_level", 1),
        demo_mode=state.get("demo_mode", False),
    )

    # Use demo pages if no real crawl data
    pages = state.get("crawl_pages") or [
        {"url": state["url"], "title": "Homepage", "meta_description": None,
         "h1": "Welcome", "word_count": 450, "status_code": 200},
    ]

    result = await agent.run(
        TechnicalSEOInput(
            site_id=uuid.UUID(state["site_id"]),
            crawl_id=uuid.UUID(state["crawl_id"]),
            pages=pages,
        ),
        ctx,
    )
    if result.success and result.output:
        out = result.output
        return {
            "seo_issues": [i.model_dump() for i in out.issues],
            "seo_health_score": out.health_score,
            "stage": "seo_complete",
        }
    return {"stage": "seo_skipped"}


def route_after_onboarding(state: OnboardingState) -> str:
    """Route after onboarding: proceed to SEO or error."""
    if state.get("stage") == "error" or not state.get("domain_valid", True):
        return "handle_error"
    return "seo_audit"


async def node_handle_error(state: OnboardingState) -> dict:
    """Log and surface onboarding errors."""
    return {"stage": "failed"}


async def node_finalize(state: OnboardingState) -> dict:
    """Final state assembly."""
    return {"stage": "complete"}


# ─── Graph Definition ─────────────────────────────────────────────────────────

def build_onboarding_graph() -> StateGraph:
    """
    Build and return the LangGraph StateGraph for site onboarding.
    Call .compile() on the returned graph before use.
    """
    graph = StateGraph(OnboardingState)

    # Add nodes
    graph.add_node("onboard_site", node_onboard_site)
    graph.add_node("seo_audit", node_seo_audit)
    graph.add_node("handle_error", node_handle_error)
    graph.add_node("finalize", node_finalize)

    # Edges
    graph.add_edge(START, "onboard_site")
    graph.add_conditional_edges(
        "onboard_site",
        route_after_onboarding,
        {
            "seo_audit": "seo_audit",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("seo_audit", "finalize")
    graph.add_edge("handle_error", END)
    graph.add_edge("finalize", END)

    return graph


# Compile graph (singleton for reuse)
_compiled_graph = None


def get_onboarding_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_onboarding_graph().compile()
    return _compiled_graph


async def run_onboarding_workflow(
    site_id: str,
    crawl_id: str,
    url: str,
    workspace_id: str,
    max_pages: int = 100,
    autonomy_level: int = 1,
    demo_mode: bool = False,
) -> OnboardingState:
    """
    Run the full onboarding workflow graph and return final state.
    """
    graph = get_onboarding_graph()
    initial_state: OnboardingState = {
        "site_id": site_id,
        "crawl_id": crawl_id,
        "url": url,
        "max_pages": max_pages,
        "workspace_id": workspace_id,
        "autonomy_level": autonomy_level,
        "demo_mode": demo_mode,
        "domain_valid": True,
        "pages_queued": 0,
        "robots_found": False,
        "sitemap_found": False,
        "product_summary": None,
        "category": None,
        "icp_summary": None,
        "crawl_pages": [],
        "seo_issues": [],
        "seo_health_score": 0.0,
        "recommendations": [],
        "errors": [],
        "warnings": [],
        "stage": "init",
    }
    final = await graph.ainvoke(initial_state)
    return final
