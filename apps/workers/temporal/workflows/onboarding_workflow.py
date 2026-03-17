"""
Temporal Workflow: Site Onboarding

Durable, resumable workflow that wraps the LangGraph onboarding graph.
Temporal provides: retries, timeouts, persistence, scheduling.
LangGraph provides: agent reasoning and orchestration.

Separation of concerns:
  Temporal = workflow durability, scheduling, retries
  LangGraph = agent reasoning logic
"""
import uuid
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


# ─── Activities ───────────────────────────────────────────────────────────────
# Activities are the actual executable units in Temporal.
# They call into our Python services/agents.


@activity.defn(name="validate_domain")
async def validate_domain_activity(url: str) -> dict:
    """Validate domain reachability."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.head(url)
            return {"valid": r.status_code < 500, "status_code": r.status_code}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@activity.defn(name="run_crawl")
async def run_crawl_activity(site_id: str, crawl_id: str, url: str, max_pages: int) -> dict:
    """
    Execute site crawl and store pages to database.
    In production: uses httpx + Playwright for rendered pages.
    """
    # Import here to avoid circular imports in activity context
    from app.tools.web_crawler import WebCrawlerTool
    tool = WebCrawlerTool()
    result = await tool.crawl(url=url, max_pages=max_pages)
    return {"pages_crawled": result.pages_crawled, "success": result.success}


@activity.defn(name="run_seo_audit")
async def run_seo_audit_activity(site_id: str, crawl_id: str) -> dict:
    """Run SEO audit on crawled data."""
    return {"audit_complete": True, "issues_found": 0}  # Simplified


@activity.defn(name="run_product_understanding")
async def run_product_understanding_activity(site_id: str, url: str) -> dict:
    """Run product understanding agents."""
    return {"product_summary": f"Product at {url}", "category": "SaaS"}


@activity.defn(name="generate_recommendations")
async def generate_recommendations_activity(site_id: str) -> dict:
    """Generate prioritized recommendations from audit data."""
    return {"recommendations_generated": 0}


@activity.defn(name="generate_initial_report")
async def generate_initial_report_activity(workspace_id: str, site_id: str) -> dict:
    """Generate initial onboarding report."""
    return {"report_generated": True}


@activity.defn(name="notify_onboarding_complete")
async def notify_onboarding_complete_activity(workspace_id: str, site_id: str, summary: dict) -> None:
    """Send notification that onboarding is complete."""
    # In production: send Slack/email notification
    pass


# ─── Workflow ─────────────────────────────────────────────────────────────────

@workflow.defn(name="SiteOnboardingWorkflow")
class SiteOnboardingWorkflow:
    """
    Durable Temporal workflow for full site onboarding.

    Steps:
    1. Validate domain
    2. Run crawl (polite, robots-aware)
    3. Run SEO audit
    4. Run product understanding
    5. Generate recommendations
    6. Generate initial report
    7. Notify team
    """

    STANDARD_RETRY = RetryPolicy(
        maximum_attempts=3,
        initial_interval=timedelta(seconds=10),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=5),
    )

    @workflow.run
    async def run(self, params: dict) -> dict:
        site_id: str = params["site_id"]
        crawl_id: str = params["crawl_id"]
        url: str = params["url"]
        workspace_id: str = params["workspace_id"]
        max_pages: int = params.get("max_pages", 100)

        workflow.logger.info(f"SiteOnboardingWorkflow starting: site={site_id} url={url}")

        # Step 1: Domain validation
        domain_result = await workflow.execute_activity(
            validate_domain_activity,
            args=[url],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.STANDARD_RETRY,
        )
        if not domain_result.get("valid"):
            return {
                "success": False,
                "error": f"Domain validation failed: {domain_result.get('error', 'unreachable')}",
                "site_id": site_id,
            }

        # Step 2: Crawl (longer timeout — can take minutes for large sites)
        await workflow.execute_activity(
            run_crawl_activity,
            args=[site_id, crawl_id, url, max_pages],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # Step 3: SEO Audit
        await workflow.execute_activity(
            run_seo_audit_activity,
            args=[site_id, crawl_id],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=self.STANDARD_RETRY,
        )

        # Step 4: Product Understanding
        await workflow.execute_activity(
            run_product_understanding_activity,
            args=[site_id, url],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=self.STANDARD_RETRY,
        )

        # Step 5: Generate Recommendations
        await workflow.execute_activity(
            generate_recommendations_activity,
            args=[site_id],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=self.STANDARD_RETRY,
        )

        # Step 6: Initial Report
        await workflow.execute_activity(
            generate_initial_report_activity,
            args=[workspace_id, site_id],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=self.STANDARD_RETRY,
        )

        # Step 7: Notify
        await workflow.execute_activity(
            notify_onboarding_complete_activity,
            args=[workspace_id, site_id, {"url": url}],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        workflow.logger.info(f"SiteOnboardingWorkflow complete: site={site_id}")
        return {"success": True, "site_id": site_id}


@workflow.defn(name="WeeklyReportWorkflow")
class WeeklyReportWorkflow:
    """
    Periodic workflow that generates weekly growth reports.
    Scheduled via Temporal cron or manual trigger.
    """

    @workflow.run
    async def run(self, params: dict) -> dict:
        workspace_id = params["workspace_id"]
        workflow.logger.info(f"WeeklyReportWorkflow: workspace={workspace_id}")
        # TODO: collect KPIs, call report agent, store report, notify
        return {"success": True, "workspace_id": workspace_id}
