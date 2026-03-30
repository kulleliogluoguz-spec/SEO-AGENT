"""
Temporal Worker Entry Point — runs inside the API container.

Built from apps/api context with WORKDIR=/app.
All imports use app.* namespace (relative to /app).
"""
import asyncio
import logging
import sys

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config.settings import get_settings
from app.workers.workflows.onboarding_workflow import (
    SiteOnboardingWorkflow,
    WeeklyReportWorkflow,
    validate_domain_activity,
    run_crawl_activity,
    run_seo_audit_activity,
    run_product_understanding_activity,
    generate_recommendations_activity,
    generate_initial_report_activity,
    notify_onboarding_complete_activity,
)

settings = get_settings()
logger = structlog.get_logger(__name__)


async def main() -> None:
    logger.info(
        "temporal_worker.starting",
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
    )

    try:
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    except Exception as e:
        logger.error("temporal_worker.connection_failed", error=str(e))
        logger.warning("temporal_worker.running_without_temporal - workflows will use direct execution fallback")
        # Don't crash — API can still serve requests without worker
        await asyncio.sleep(3600)  # Keep container alive for restart
        return

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[SiteOnboardingWorkflow, WeeklyReportWorkflow],
        activities=[
            validate_domain_activity,
            run_crawl_activity,
            run_seo_audit_activity,
            run_product_understanding_activity,
            generate_recommendations_activity,
            generate_initial_report_activity,
            notify_onboarding_complete_activity,
        ],
    )

    logger.info("temporal_worker.ready", task_queue=settings.temporal_task_queue)
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
