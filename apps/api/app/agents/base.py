"""
Base agent infrastructure for AI CMO OS.

Every agent in the system inherits from BaseAgent or one of its subclasses.
This ensures consistent:
  - Input/output schema validation
  - Observability (structured logging, run tracking)
  - Policy gating
  - Retry handling
  - Token usage tracking
  - Failure reporting
"""
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar, Generic, TypeVar

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentMetadata(BaseModel):
    """Static metadata declared by each agent class."""
    name: str
    layer: int
    description: str
    version: str = "1.0"
    requires_llm: bool = True
    max_retries: int = 3
    timeout_seconds: int = 120
    autonomy_min_level: int = 0  # Minimum autonomy level required to execute


class AgentRunContext(BaseModel):
    """Runtime context passed to every agent invocation."""
    workspace_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    workflow_run_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    autonomy_level: int = 1
    trace_id: str | None = None
    demo_mode: bool = False
    dry_run: bool = False


class AgentResult(BaseModel, Generic[OutputT]):
    """Standardized agent result wrapper."""
    success: bool
    output: OutputT | None = None
    error: str | None = None
    tokens_used: int = 0
    duration_ms: int = 0
    agent_name: str = ""
    trace_id: str | None = None
    warnings: list[str] = []
    policy_flags: list[str] = []


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all AI CMO OS agents.

    Subclasses must:
    1. Declare `metadata: ClassVar[AgentMetadata]`
    2. Implement `async def _execute(input_data, context) -> OutputT`
    """

    metadata: ClassVar[AgentMetadata]

    def __init__(
        self,
        llm_client: Any | None = None,
        db_session: Any | None = None,
    ) -> None:
        self._llm = llm_client
        self._db = db_session
        self._log = structlog.get_logger(self.__class__.__name__)

    async def run(
        self,
        input_data: InputT,
        context: AgentRunContext | None = None,
    ) -> AgentResult:
        """
        Public entry point. Wraps _execute with:
        - Policy gating
        - Timing
        - Error handling
        - Logging
        """
        ctx = context or AgentRunContext()
        trace_id = ctx.trace_id or str(uuid.uuid4())[:8]
        start = time.monotonic()

        self._log.info(
            "agent.start",
            agent=self.metadata.name,
            layer=self.metadata.layer,
            trace_id=trace_id,
            workspace_id=str(ctx.workspace_id),
        )

        # Policy gate: autonomy level check
        if ctx.autonomy_level < self.metadata.autonomy_min_level:
            return AgentResult(
                success=False,
                error=f"Autonomy level {ctx.autonomy_level} insufficient; requires {self.metadata.autonomy_min_level}",
                agent_name=self.metadata.name,
                trace_id=trace_id,
            )

        # Dry run short-circuit
        if ctx.dry_run:
            self._log.info("agent.dry_run", agent=self.metadata.name)
            return AgentResult(
                success=True,
                agent_name=self.metadata.name,
                trace_id=trace_id,
            )

        try:
            output = await self._execute(input_data, ctx)
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log.info(
                "agent.complete",
                agent=self.metadata.name,
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
            return AgentResult(
                success=True,
                output=output,
                duration_ms=duration_ms,
                agent_name=self.metadata.name,
                trace_id=trace_id,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log.error(
                "agent.error",
                agent=self.metadata.name,
                error=str(exc),
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
            return AgentResult(
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
                agent_name=self.metadata.name,
                trace_id=trace_id,
            )

    @abstractmethod
    async def _execute(self, input_data: InputT, context: AgentRunContext) -> OutputT:
        """Agent-specific implementation. Must be overridden."""
        ...

    def _build_llm_prompt(self, template: str, **kwargs: Any) -> str:
        """Simple template substitution helper."""
        return template.format(**kwargs)


class LLMAgent(BaseAgent[InputT, OutputT]):
    """
    Extended base for agents that call the LLM.
    Adds structured output parsing and token tracking.
    """

    async def _call_llm(
        self,
        system: str,
        user: str,
        response_schema: type[BaseModel] | None = None,
        max_tokens: int = 2048,
    ) -> tuple[str, int]:
        """
        Call the Anthropic API.
        Returns (content_text, tokens_used).
        In demo mode, returns placeholder text.
        """
        if not self._llm:
            return self._demo_response(user), 0

        from app.core.config.settings import get_settings
        settings = get_settings()

        messages = [{"role": "user", "content": user}]

        if response_schema:
            schema_hint = (
                f"\n\nRespond ONLY with valid JSON matching this schema:\n"
                f"{response_schema.model_json_schema()}"
            )
            system = system + schema_hint

        response = await self._llm.messages.create(
            model=settings.llm_default_model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return content, tokens

    def _demo_response(self, prompt: str) -> str:
        """Fallback content for demo mode when no LLM key is configured."""
        return (
            f"[DEMO] This is a placeholder response for agent {self.metadata.name}. "
            "Configure ANTHROPIC_API_KEY for real AI-powered output."
        )

    async def _call_llm_structured(
        self,
        system: str,
        user: str,
        response_schema: type[OutputT],
        max_tokens: int = 2048,
    ) -> tuple[OutputT | None, int]:
        """Call LLM and parse response into a Pydantic model."""
        import json

        text, tokens = await self._call_llm(system, user, response_schema, max_tokens)
        if not text or "[DEMO]" in text:
            return None, tokens

        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]

        try:
            data = json.loads(cleaned)
            return response_schema.model_validate(data), tokens
        except Exception as e:
            self._log.warning("llm_parse_error", agent=self.metadata.name, error=str(e))
            return None, tokens
