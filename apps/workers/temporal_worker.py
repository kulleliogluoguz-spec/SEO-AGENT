"""
Temporal Worker — registers all workflows and activities.

Run with:
    python temporal_worker.py

Or via Docker:
    docker compose up worker
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from apps.api.app.core.config.settings import get_settings

# Import all workflows
from apps.api.app.workers.temporal.workflows.onboarding_workflow import (
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


async def main():
    logger.info(
        "temporal_worker.starting",
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
    )

    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            SiteOnboardingWorkflow,
            WeeklyReportWorkflow,
        ],
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
