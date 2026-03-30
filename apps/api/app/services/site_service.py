"""SiteService — site onboarding and workflow trigger."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config.settings import get_settings

settings = get_settings()


class SiteService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def trigger_onboarding_workflow(
        self, site_id: uuid.UUID, crawl_id: uuid.UUID
    ) -> str | None:
        """
        Start the Temporal onboarding workflow.
        Returns workflow run ID or None if Temporal not available.
        """
        from sqlalchemy import select
        from app.models.models import Site

        site_result = await self._db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        if not site:
            return None

        try:
            from temporalio.client import Client
            client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)

            handle = await client.start_workflow(
                "SiteOnboardingWorkflow",
                args=[{
                    "site_id": str(site_id),
                    "crawl_id": str(crawl_id),
                    "url": site.url,
                    "workspace_id": str(site.workspace_id),
                    "max_pages": 100,
                }],
                id=f"onboarding-{site_id}",
                task_queue=settings.temporal_task_queue,
            )
            return handle.id
        except Exception:
            # Temporal not running in dev — fall back to direct execution
            import asyncio
            asyncio.create_task(self._direct_onboard(site, crawl_id))
            return None

    async def _direct_onboard(self, site, crawl_id: uuid.UUID) -> None:
        """Fallback: run onboarding directly when Temporal is unavailable."""
        from app.workflows.onboarding_graph import run_onboarding_workflow
        from app.models.models import Site, SiteStatus, Crawl, CrawlStatus
        from sqlalchemy import select

        try:
            state = await run_onboarding_workflow(
                site_id=str(site.id),
                crawl_id=str(crawl_id),
                url=site.url,
                workspace_id=str(site.workspace_id),
                demo_mode=settings.demo_mode,
            )

            # Update site
            site_result = await self._db.execute(select(Site).where(Site.id == site.id))
            db_site = site_result.scalar_one_or_none()
            if db_site:
                db_site.status = SiteStatus.ACTIVE
                db_site.product_summary = state.get("product_summary")
                db_site.category = state.get("category")
                db_site.icp_summary = state.get("icp_summary")

            # Update crawl
            crawl_result = await self._db.execute(select(Crawl).where(Crawl.id == crawl_id))
            db_crawl = crawl_result.scalar_one_or_none()
            if db_crawl:
                db_crawl.status = CrawlStatus.COMPLETED
                db_crawl.pages_crawled = state.get("pages_queued", 0)

            await self._db.commit()
        except Exception as e:
            import structlog
            structlog.get_logger().error("direct_onboard_failed", error=str(e))
