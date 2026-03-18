"""
Tool-Calling Layer — Structured tool definitions for AI agent use.

Features:
- OpenAI-compatible tool schemas
- Safe execution wrappers with timeout/retry
- Permission boundaries per tool
- Execution tracing
- Tool result formatting
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class ToolPermission(str, Enum):
    READ_ONLY = "read_only"         # Can read data
    WRITE_DRAFT = "write_draft"     # Can create drafts (needs approval)
    WRITE_APPROVED = "write_approved"  # Can write after approval
    EXECUTE = "execute"             # Can trigger actions
    ADMIN = "admin"                 # Full access


class ToolCategory(str, Enum):
    DATA_RETRIEVAL = "data_retrieval"
    ANALYSIS = "analysis"
    CONTENT = "content"
    CONNECTOR = "connector"
    INTERNAL = "internal"


@dataclass
class ToolDefinition:
    """A tool that AI agents can call."""
    name: str
    description: str
    parameters: dict[str, Any]       # JSON Schema for parameters
    category: ToolCategory = ToolCategory.INTERNAL
    permission: ToolPermission = ToolPermission.READ_ONLY
    timeout_seconds: float = 30.0
    max_retries: int = 2
    enabled: bool = True
    requires_approval: bool = False  # Must go through approval queue
    tags: list[str] = field(default_factory=list)

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolExecution:
    """Record of a tool execution."""
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approved: bool = False
    timestamp: float = field(default_factory=time.time)


# Type for tool handler functions
ToolHandler = Callable[..., Coroutine[Any, Any, Any]]


class ToolRegistry:
    """Registry of all tools available to AI agents."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._execution_log: list[ToolExecution] = []
        self._load_defaults()

    def register(self, definition: ToolDefinition, handler: Optional[ToolHandler] = None) -> None:
        self._tools[definition.name] = definition
        if handler:
            self._handlers[definition.name] = handler

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def get_tools_for_role(self, permission_level: ToolPermission) -> list[ToolDefinition]:
        """Get tools accessible at a given permission level."""
        perm_hierarchy = {
            ToolPermission.READ_ONLY: 0,
            ToolPermission.WRITE_DRAFT: 1,
            ToolPermission.WRITE_APPROVED: 2,
            ToolPermission.EXECUTE: 3,
            ToolPermission.ADMIN: 4,
        }
        max_level = perm_hierarchy.get(permission_level, 0)
        return [
            t for t in self._tools.values()
            if t.enabled and perm_hierarchy.get(t.permission, 0) <= max_level
        ]

    def get_openai_schemas(self, tools: Optional[list[str]] = None) -> list[dict]:
        """Get OpenAI-format tool schemas."""
        if tools:
            return [
                self._tools[name].to_openai_schema()
                for name in tools
                if name in self._tools and self._tools[name].enabled
            ]
        return [t.to_openai_schema() for t in self._tools.values() if t.enabled]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        trace_id: str = "",
        autonomy_level: int = 1,
    ) -> ToolExecution:
        """Execute a tool with safety checks."""
        definition = self._tools.get(tool_name)
        if not definition:
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                error=f"Tool not found: {tool_name}",
                trace_id=trace_id,
            )

        if not definition.enabled:
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                error=f"Tool disabled: {tool_name}",
                trace_id=trace_id,
            )

        # Check if approval is required
        if definition.requires_approval and autonomy_level < 3:
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                error="Tool requires approval. Queued for human review.",
                approved=False,
                trace_id=trace_id,
            )

        handler = self._handlers.get(tool_name)
        if not handler:
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                error=f"No handler registered for tool: {tool_name}",
                trace_id=trace_id,
            )

        # Execute with retry and timeout
        start = time.time()
        last_error = None
        for attempt in range(definition.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    handler(**arguments),
                    timeout=definition.timeout_seconds,
                )
                execution = ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    duration_ms=(time.time() - start) * 1000,
                    approved=True,
                    trace_id=trace_id,
                )
                self._execution_log.append(execution)
                return execution
            except asyncio.TimeoutError:
                last_error = f"Timeout after {definition.timeout_seconds}s (attempt {attempt + 1})"
                logger.warning(f"Tool {tool_name} timeout: attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool {tool_name} error: {e} (attempt {attempt + 1})")

        execution = ToolExecution(
            tool_name=tool_name,
            arguments=arguments,
            error=last_error,
            duration_ms=(time.time() - start) * 1000,
            trace_id=trace_id,
        )
        self._execution_log.append(execution)
        return execution

    def get_execution_log(self, limit: int = 50) -> list[dict]:
        return [
            {
                "tool": ex.tool_name,
                "args": ex.arguments,
                "result_preview": str(ex.result)[:200] if ex.result else None,
                "error": ex.error,
                "duration_ms": ex.duration_ms,
                "trace_id": ex.trace_id,
                "approved": ex.approved,
            }
            for ex in self._execution_log[-limit:]
        ]

    def list_all(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "permission": t.permission.value,
                "enabled": t.enabled,
                "requires_approval": t.requires_approval,
            }
            for t in self._tools.values()
        ]

    # ─── Default Tool Definitions ─────────────────────────────────

    def _load_defaults(self) -> None:
        """Register default platform tools."""

        self.register(ToolDefinition(
            name="get_site_crawl_data",
            description="Retrieve crawl data for a site including pages, metadata, and technical SEO signals.",
            parameters={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string", "description": "The site UUID"},
                    "include_pages": {"type": "boolean", "default": True},
                    "max_pages": {"type": "integer", "default": 100},
                },
                "required": ["site_id"],
            },
            category=ToolCategory.DATA_RETRIEVAL,
            permission=ToolPermission.READ_ONLY,
        ))

        self.register(ToolDefinition(
            name="get_recommendations",
            description="Retrieve existing recommendations for a site.",
            parameters={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "approved", "rejected", "implemented"]},
                },
                "required": ["site_id"],
            },
            category=ToolCategory.DATA_RETRIEVAL,
            permission=ToolPermission.READ_ONLY,
        ))

        self.register(ToolDefinition(
            name="create_recommendation",
            description="Create a new recommendation for a site. Goes into the approval queue.",
            parameters={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string"},
                    "title": {"type": "string"},
                    "category": {"type": "string"},
                    "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                    "description": {"type": "string"},
                    "evidence": {"type": "string"},
                    "implementation_steps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["site_id", "title", "category", "priority", "description"],
            },
            category=ToolCategory.CONTENT,
            permission=ToolPermission.WRITE_DRAFT,
            requires_approval=True,
        ))

        self.register(ToolDefinition(
            name="create_content_draft",
            description="Create a content draft. Always goes to the review queue.",
            parameters={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string"},
                    "title": {"type": "string"},
                    "content_type": {"type": "string", "enum": ["blog_post", "landing_page", "guide", "comparison"]},
                    "body": {"type": "string"},
                    "target_keywords": {"type": "array", "items": {"type": "string"}},
                    "meta_description": {"type": "string"},
                },
                "required": ["site_id", "title", "content_type", "body"],
            },
            category=ToolCategory.CONTENT,
            permission=ToolPermission.WRITE_DRAFT,
            requires_approval=True,
        ))

        self.register(ToolDefinition(
            name="get_analytics_data",
            description="Retrieve analytics data (GA4, GSC) for a site.",
            parameters={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string"},
                    "source": {"type": "string", "enum": ["ga4", "gsc", "all"]},
                    "date_range": {"type": "string", "enum": ["7d", "30d", "90d"]},
                    "metrics": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["site_id"],
            },
            category=ToolCategory.CONNECTOR,
            permission=ToolPermission.READ_ONLY,
        ))

        self.register(ToolDefinition(
            name="get_competitor_data",
            description="Retrieve competitor analysis data.",
            parameters={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string"},
                    "competitor_urls": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["site_id"],
            },
            category=ToolCategory.DATA_RETRIEVAL,
            permission=ToolPermission.READ_ONLY,
        ))

        self.register(ToolDefinition(
            name="send_notification",
            description="Send a notification to the workspace (e.g., Slack, email).",
            parameters={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["slack", "email", "in_app"]},
                    "message": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["low", "normal", "high"]},
                },
                "required": ["channel", "message"],
            },
            category=ToolCategory.CONNECTOR,
            permission=ToolPermission.EXECUTE,
            requires_approval=True,
        ))

        logger.info(f"ToolRegistry loaded {len(self._tools)} default tools")


# Singleton
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
