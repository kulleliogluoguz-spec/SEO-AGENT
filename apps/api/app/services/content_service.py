"""
ContentService — business logic for content brief and generation.
"""
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ContentAsset, ContentStatus, User
from app.agents.layer8.content_agents import (
    ContentBriefAgent,
    ContentBriefInput,
    LongFormWriterAgent,
    LongFormWriterInput,
)
from app.agents.base import AgentRunContext
from app.core.config.settings import get_settings

settings = get_settings()


class ContentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _get_llm_client(self):
        if not settings.anthropic_api_key:
            return None
        import anthropic
        return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def create_brief(
        self,
        site_id: uuid.UUID,
        content_type: str,
        topic: str,
        target_keyword: str | None,
        tone: str,
        word_count_target: int | None,
        notes: str | None,
        created_by: User,
    ) -> ContentAsset:
        """Generate a content brief using the ContentBriefAgent."""
        llm = self._get_llm_client()
        agent = ContentBriefAgent(llm_client=llm)
        ctx = AgentRunContext(
            demo_mode=settings.demo_mode,
            autonomy_level=settings.autonomy_default_level,
        )

        result = await agent.run(
            ContentBriefInput(
                site_id=site_id,
                content_type=content_type,
                topic=topic,
                target_keyword=target_keyword,
                tone=tone,
                word_count_target=word_count_target,
                notes=notes,
            ),
            ctx,
        )

        brief_data: dict[str, Any] = {}
        title = topic
        if result.success and result.output:
            brief_data = result.output.model_dump()
            title = result.output.title

        # Determine workspace from site
        from sqlalchemy import select
        from app.models.models import Site
        site_result = await self._db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        workspace_id = site.workspace_id if site else uuid.uuid4()

        asset = ContentAsset(
            workspace_id=workspace_id,
            site_id=site_id,
            title=title,
            asset_type=content_type,
            status=ContentStatus.DRAFT,
            brief=brief_data,
            generated_by_agent="ContentBriefAgent",
        )
        self._db.add(asset)
        await self._db.commit()
        await self._db.refresh(asset)
        return asset

    async def generate_from_brief(
        self,
        brief_id: uuid.UUID,
        model: str | None = None,
    ) -> ContentAsset:
        """Generate content from an existing brief asset."""
        from sqlalchemy import select
        result = await self._db.execute(
            select(ContentAsset).where(ContentAsset.id == brief_id)
        )
        brief_asset = result.scalar_one_or_none()
        if not brief_asset:
            raise ValueError(f"Brief {brief_id} not found")

        # Reconstruct brief object
        from app.agents.layer8.content_agents import ContentBriefOutput
        brief_obj = ContentBriefOutput.model_validate(brief_asset.brief) if brief_asset.brief else None

        llm = self._get_llm_client()
        agent = LongFormWriterAgent(llm_client=llm)
        ctx = AgentRunContext(
            demo_mode=settings.demo_mode,
            autonomy_level=settings.autonomy_default_level,
        )

        if brief_obj:
            write_result = await agent.run(
                LongFormWriterInput(brief=brief_obj),
                ctx,
            )
        else:
            write_result = None

        content = None
        flags = []
        risk = 0.0
        if write_result and write_result.success and write_result.output:
            content = write_result.output.content_markdown
            flags = write_result.output.compliance_flags
            risk = write_result.output.risk_score

        asset = ContentAsset(
            workspace_id=brief_asset.workspace_id,
            site_id=brief_asset.site_id,
            title=brief_asset.title,
            asset_type=brief_asset.asset_type,
            status=ContentStatus.REVIEW,  # Always goes to review
            content=content,
            brief=brief_asset.brief,
            compliance_flags=flags,
            risk_score=risk,
            generated_by_agent="LongFormWriterAgent",
        )
        self._db.add(asset)
        await self._db.commit()
        await self._db.refresh(asset)
        return asset
