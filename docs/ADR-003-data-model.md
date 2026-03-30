# ADR-003: Data Model Design

## Status
Accepted

## Context
Multi-tenant platform with workspaces, sites, crawls, recommendations, content, approvals.

## Decision
- Workspace-scoped data model (all entities have workspace_id)
- Soft delete not used by default (adds complexity); archived status instead
- JSONB for flexible metadata, structured fields for queryable data
- pgvector for future embedding/semantic search
- Audit logs as append-only table

## Consequences
- workspace_id filters required on all queries (enforced at service layer)
- JSONB fields are flexible but not strongly typed at DB level
