# ADR-002: Agent Orchestration — LangGraph + Temporal Split

## Status
Accepted

## Context
We need both reasoning-level orchestration (agent chains, conditional routing) and durable execution (retries, scheduling, long-running jobs).

## Decision
Use LangGraph for reasoning graphs and Temporal for durable workflows. Keep them cleanly separated: LangGraph subgraphs are called from Temporal activities.

## Consequences
- Two orchestration systems to learn and operate
- Clear separation of concerns: reasoning vs durability
- Temporal Cloud available for managed production deployment
