"""
Connector Registry — Global catalog of available connector types.

Connectors register themselves on import. The registry provides
discovery, instantiation, and metadata for the connector UI.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Type

if TYPE_CHECKING:
    from connector_sdk.base import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Registry of all available connector types."""

    _connectors: dict[str, Type["BaseConnector"]] = {}

    @classmethod
    def register(cls, connector_class: Type["BaseConnector"]) -> Type["BaseConnector"]:
        """Register a connector class. Can be used as a decorator."""
        source_type = connector_class.source_type
        if source_type in cls._connectors:
            logger.warning(f"Overwriting connector registration for: {source_type}")
        cls._connectors[source_type] = connector_class
        logger.debug(f"Registered connector: {source_type}")
        return connector_class

    @classmethod
    def get(cls, source_type: str) -> Type["BaseConnector"] | None:
        """Get a connector class by source_type."""
        return cls._connectors.get(source_type)

    @classmethod
    def create(cls, source_type: str, **kwargs: Any) -> "BaseConnector | None":
        """Instantiate a connector by source_type."""
        klass = cls.get(source_type)
        if klass is None:
            logger.error(f"No connector registered for source_type: {source_type}")
            return None
        return klass(**kwargs)

    @classmethod
    def list_available(cls) -> list[dict[str, str]]:
        """List all registered connectors with metadata."""
        return [
            {
                "source_type": klass.source_type,
                "display_name": klass.display_name,
                "description": klass.description,
                "compliance_mode": klass.compliance_mode.value,
            }
            for klass in cls._connectors.values()
        ]

    @classmethod
    def list_by_compliance_mode(cls, mode: str) -> list[Type["BaseConnector"]]:
        """List connectors filtered by compliance mode."""
        return [
            klass
            for klass in cls._connectors.values()
            if klass.compliance_mode.value == mode
        ]
