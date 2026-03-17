# ADR-001: Stack Selection

## Status
Accepted

## Context
We need a full-stack for an AI-powered growth platform with: multi-agent orchestration, durable workflows, async crawling, strong typing, and a modern dashboard UI.

## Decision
- **Python 3.12 + FastAPI**: Best-in-class async Python, excellent Pydantic integration, strong typing
- **SQLAlchemy 2.x + Alembic**: Mature ORM with async support, battle-tested migrations
- **LangGraph**: Best open-source framework for stateful multi-agent reasoning graphs
- **Temporal**: Industry-standard durable workflow engine with excellent Python SDK
- **PostgreSQL + pgvector**: Relational + vector search in one database
- **Next.js 14 App Router**: Modern React with SSR, excellent TypeScript support
- **Tailwind CSS**: Utility-first CSS for rapid, consistent UI development

## Consequences
- Temporal adds operational complexity but provides essential durability for long crawls and retries
- LangGraph is newer but well-maintained and fits the agent graph model well
- pgvector avoids a separate vector database for the initial version
