"""
Connector SDK — Unified source ingestion interface for AI Growth OS.

Every data source connector must implement BaseConnector and declare
its compliance mode. See docs/connectors/connector-sdk.md.
"""
from connector_sdk.base import (
    BaseConnector,
    ComplianceMode,
    ConnectorConfig,
    RawDocument,
    ValidationResult,
    ConnectionTestResult,
    RateLimitPolicy,
    HealthStatus,
    make_doc_id,
)
from connector_sdk.registry import ConnectorRegistry

__all__ = [
    "BaseConnector",
    "ComplianceMode",
    "ConnectorConfig",
    "RawDocument",
    "ValidationResult",
    "ConnectionTestResult",
    "RateLimitPolicy",
    "HealthStatus",
    "ConnectorRegistry",
    "make_doc_id",
]
