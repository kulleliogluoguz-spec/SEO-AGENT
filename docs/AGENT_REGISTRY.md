# Agent Registry — AI CMO OS

138 agents across 13 layers. Each agent has a single responsibility,
typed inputs/outputs, policy gating, and observability hooks.

## Layer Summary

| Layer | Name | Agents | Purpose |
|-------|------|--------|---------|
| 0 | Platform Control | 12 | Supervision, routing, policy, compliance |
| 1 | Onboarding & Intelligence | 13 | Crawling, metadata, content normalization |
| 2 | Product Understanding | 12 | Product summary, ICP, personas, positioning |
| 3 | Competitor Intel | 10 | Discovery, clustering, battlecards |
| 4 | Search Growth (SEO) | 13 | Technical SEO, on-page, content gaps |
| 5 | GEO/AEO/AI Visibility | 10 | AI discoverability (experimental) |
| 6 | Analytics/Attribution | 11 | GA4, GSC, KPIs, trends, anomalies |
| 7 | Content Strategy | 10 | Briefs, editorial calendar, audience mapping |
| 8 | Content Production | 13 | Writing, editing, compliance, scoring |
| 9 | Distribution & Operations | 9 | Planning, scheduling, approval routing |
| 10 | Experimentation | 7 | Hypothesis, variants, metrics, review |
| 11 | Reporting/Executive | 8 | Daily/weekly/monthly reports, narratives |
| 12 | Quality/Evaluation | 10 | Prompt eval, QA, hallucination risk |

## Agent Design Principles

1. **Single responsibility** — each agent does one thing well
2. **Typed contracts** — Pydantic input/output schemas always
3. **Policy awareness** — autonomy level checked before execution
4. **Demo mode** — all agents work without LLM in demo/test mode
5. **Observability** — structured logging at start/complete/error
6. **Failure isolation** — errors return AgentResult, never crash callers

## Adding a New Agent

1. Create file in the appropriate `agents/layerN/` directory
2. Define `InputSchema(BaseModel)` and `OutputSchema(BaseModel)`
3. Subclass `LLMAgent[Input, Output]` or `BaseAgent[Input, Output]`
4. Declare `metadata: ClassVar[AgentMetadata]`
5. Implement `async def _execute(input_data, context) -> Output`
6. Add entry to `agents/registry.py`
7. Add unit tests

## Complete Agent List

### Layer 0 — Platform Control
1. **SystemSupervisorAgent** — Top-level workflow supervisor
2. **WorkflowRouterAgent** — Routes incoming work to sub-graphs
3. **WorkspaceContextAgent** — Loads workspace context for agents
4. **PolicyGateAgent** — Autonomy policy enforcement
5. **ComplianceGuardianAgent** — Content/action compliance review
6. **ApprovalGateAgent** — Creates and manages approval requests
7. **TraceNarratorAgent** — Human-readable execution traces
8. **FailureRecoveryAgent** — Failure handling and fallback strategies
9. **CostBudgetAgent** — LLM token usage tracking and budgets
10. **ToolPermissionAgent** — Tool-level permission enforcement
11. **MemoryCompactionAgent** — Long conversation history compaction
12. **ContextShapingAgent** — Context window management

### Layer 1 — Onboarding & Intelligence
13. **SiteOnboardingAgent** — Full pipeline orchestrator
14. **DomainValidationAgent** — DNS, HTTPS, redirect validation
15. **RobotsSitemapDiscoveryAgent** — robots.txt and sitemap parsing
16. **CrawlPlanningAgent** — Scope, depth, page prioritization
17. **PageClassificationAgent** — Page type classification
18. **RenderFallbackDecisionAgent** — Playwright rendering decisions
19. **ContentNormalizationAgent** — HTML to clean structured content
20. **MetadataExtractionAgent** — Title, OG, Twitter card extraction
21. **StructuredDataExtractionAgent** — JSON-LD and microdata
22. **InternalLinkGraphAgent** — Link graph analysis
23. **SiteHealthScoringAgent** — Overall site health scoring
24. **CrawlEvidenceAgent** — Evidence collection for recommendations
25. **ScreenshotCaptureAgent** — Playwright screenshot capture

### Layer 2 — Product Understanding
26. **ProductUnderstandingAgent** — Product summary synthesis
27. **ProductCategoryAgent** — Category/subcategory inference
28. **ValuePropExtractionAgent** — Value proposition extraction
29. **PricingSignalAgent** — Pricing model detection
30. **ICPInferenceAgent** — Ideal Customer Profile inference
31. **PersonaInferenceAgent** — Buyer persona drafting
32. **JTBDExtractionAgent** — Jobs-to-be-Done extraction
33. **ObjectionInferenceAgent** — Buyer objection inference
34. **TrustSignalInferenceAgent** — Trust signal identification
35. **MessagingFrameworkAgent** — Messaging framework drafting
36. **PositioningDraftAgent** — Positioning statement generation
37. **OfferAnalysisAgent** — Feature/benefit/outcome analysis

### Layer 3 — Competitor Intel
38. **CompetitorDiscoveryAgent** — Direct/indirect competitor discovery
39. **CompetitorClusteringAgent** — Competitor category clustering
40. **DirectVsIndirectCompetitorAgent** — Classification
41. **AlternativeSolutionMapAgent** — Alternative solution mapping
42. **CompetitorMessagingAgent** — Competitor messaging analysis
43. **CompetitorFeatureMatrixAgent** — Feature comparison matrix
44. **CompetitorContentPatternAgent** — Content pattern analysis
45. **BattlecardAgent** — Sales battlecard generation
46. **ComparisonNarrativeAgent** — "Us vs them" narratives
47. **CategoryLandscapeAgent** — Full category map

### Layer 4 — Search Growth (SEO)
48. **TechnicalSEOAuditAgent** — Technical SEO issues
49. **OnPageSEOAuditAgent** — On-page SEO audit
50. **InternalLinkingStrategyAgent** — Internal link recommendations
51. **InformationArchitectureAgent** — IA improvement recommendations
52. **TopicClusterAgent** — Topic cluster architecture
53. **ContentGapAgent** — Content gap analysis
54. **PageRefreshOpportunityAgent** — Content refresh identification
55. **FAQOpportunityAgent** — FAQ content opportunities
56. **GlossaryOpportunityAgent** — Glossary page opportunities
57. **SchemaOpportunityAgent** — Structured data opportunities
58. **CTRImprovementAgent** — Title/meta CTR improvements
59. **RecommendationPrioritizationAgent** — Priority scoring
60. **SearchBacklogBuilderAgent** — Prioritized search backlog

### Layer 5 — GEO/AEO/AI Visibility ⚠️ Experimental
61. **AIVisibilityAgent** — Overall AI visibility assessment
62. **CitationReadinessAgent** — LLM citation readiness
63. **AnswerSurfaceCoverageAgent** — Answer surface coverage
64. **CategoryRecommendationLikelihoodAgent** — AI recommendation likelihood
65. **BrandEntityConsistencyAgent** — Brand entity consistency
66. **SourceabilityImprovementAgent** — LLM sourceability improvements
67. **UseCaseCoverageAgent** — Use case page coverage
68. **ComparisonCoverageAgent** — Comparison page coverage
69. **FAQCoverageAgent** — FAQ coverage for AI surfaces
70. **AIVisibilityBacklogAgent** — AI visibility improvement backlog

> **Note**: GEO/AEO agents produce directional signals based on content analysis. External AI answer surface measurement is not available without third-party tooling. All outputs are labeled as experimental.

### Layer 6 — Analytics/Attribution
71-81: Search Console ingestion, GA4 ingestion, KPI aggregation, trends, anomalies, landing page performance, query opportunities, content performance, channel attribution, funnel summary, metrics narrative

### Layer 7 — Content Strategy
82-91: Content strategy, editorial calendar, content brief, blog brief, comparison page brief, landing page variants, FAQ draft, newsletter angle, offer messaging variants, audience intent mapping

### Layer 8 — Content Production
92-104: Long-form writer, landing page copy, social post writer, Reddit draft, LinkedIn draft, X thread draft, Product Hunt copy, outreach email, content editor, tone consistency, claim evidence, content scoring, content revision

### Layer 9 — Distribution & Operations
105-113: Distribution planner, channel fit scoring, publish package, CMS prep, social schedule prep, approval queue routing, low-risk automation, notification, campaign assembly

### Layer 10 — Experimentation
114-120: Experiment designer, hypothesis, variant generation, success metrics, prioritization, review, summary

### Layer 11 — Reporting/Executive
121-128: Daily summary, weekly report, monthly summary, opportunity digest, risk digest, what changed, next actions, narrative synthesis

### Layer 12 — Quality/Evaluation
129-138: Prompt evaluation, recommendation quality, content quality, tool reliability, workflow regression, hallucination risk, schema validation, output critic, self review, release readiness
