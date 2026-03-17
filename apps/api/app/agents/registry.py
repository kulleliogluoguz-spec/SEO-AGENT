"""
Agent Registry — canonical list of all agents in AI CMO OS.

Every agent is registered here with its layer, name, and description.
This registry is used by:
  - The workflow router
  - The admin UI
  - Observability dashboards
  - Documentation generation
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentEntry:
    id: int
    name: str
    layer: int
    layer_name: str
    description: str
    module_path: str


AGENT_REGISTRY: list[AgentEntry] = [
    # ── LAYER 0: Platform Control ───────────────────────────────────────────
    AgentEntry(1, "SystemSupervisorAgent", 0, "Platform Control", "Top-level workflow supervisor; routes tasks, monitors system health", "agents.layer0.supervisor"),
    AgentEntry(2, "WorkflowRouterAgent", 0, "Platform Control", "Routes incoming work requests to appropriate sub-graphs", "agents.layer0.router"),
    AgentEntry(3, "WorkspaceContextAgent", 0, "Platform Control", "Loads and shapes workspace context for downstream agents", "agents.layer0.workspace_context"),
    AgentEntry(4, "PolicyGateAgent", 0, "Platform Control", "Evaluates actions against workspace autonomy policy", "agents.layer0.policy_gate"),
    AgentEntry(5, "ComplianceGuardianAgent", 0, "Platform Control", "Reviews content and actions for compliance violations", "agents.layer0.compliance"),
    AgentEntry(6, "ApprovalGateAgent", 0, "Platform Control", "Creates approval requests and blocks execution pending review", "agents.layer0.approval_gate"),
    AgentEntry(7, "TraceNarratorAgent", 0, "Platform Control", "Generates human-readable traces of agent execution paths", "agents.layer0.trace_narrator"),
    AgentEntry(8, "FailureRecoveryAgent", 0, "Platform Control", "Handles agent failures, retries, and fallback strategies", "agents.layer0.failure_recovery"),
    AgentEntry(9, "CostBudgetAgent", 0, "Platform Control", "Tracks token usage and enforces LLM cost budgets", "agents.layer0.cost_budget"),
    AgentEntry(10, "ToolPermissionAgent", 0, "Platform Control", "Enforces tool-level permissions per autonomy level", "agents.layer0.tool_permission"),
    AgentEntry(11, "MemoryCompactionAgent", 0, "Platform Control", "Compacts agent conversation history for long workflows", "agents.layer0.memory_compaction"),
    AgentEntry(12, "ContextShapingAgent", 0, "Platform Control", "Shapes and truncates context windows for downstream agents", "agents.layer0.context_shaping"),

    # ── LAYER 1: Onboarding & Intelligence ──────────────────────────────────
    AgentEntry(13, "SiteOnboardingAgent", 1, "Onboarding & Intelligence", "Orchestrates full site onboarding pipeline", "agents.layer1.site_onboarding"),
    AgentEntry(14, "DomainValidationAgent", 1, "Onboarding & Intelligence", "Validates domain, resolves DNS, checks HTTPS, detects redirects", "agents.layer1.domain_validation"),
    AgentEntry(15, "RobotsSitemapDiscoveryAgent", 1, "Onboarding & Intelligence", "Parses robots.txt and discovers sitemap files", "agents.layer1.robots_sitemap"),
    AgentEntry(16, "CrawlPlanningAgent", 1, "Onboarding & Intelligence", "Plans crawl scope, depth, and page prioritization", "agents.layer1.crawl_planning"),
    AgentEntry(17, "PageClassificationAgent", 1, "Onboarding & Intelligence", "Classifies pages by type: home, product, blog, landing, etc.", "agents.layer1.page_classification"),
    AgentEntry(18, "RenderFallbackDecisionAgent", 1, "Onboarding & Intelligence", "Decides whether Playwright rendering is needed for a page", "agents.layer1.render_fallback"),
    AgentEntry(19, "ContentNormalizationAgent", 1, "Onboarding & Intelligence", "Normalizes raw HTML to clean structured content", "agents.layer1.content_normalization"),
    AgentEntry(20, "MetadataExtractionAgent", 1, "Onboarding & Intelligence", "Extracts titles, descriptions, Open Graph, Twitter cards", "agents.layer1.metadata_extraction"),
    AgentEntry(21, "StructuredDataExtractionAgent", 1, "Onboarding & Intelligence", "Extracts JSON-LD and microdata structured schemas", "agents.layer1.structured_data"),
    AgentEntry(22, "InternalLinkGraphAgent", 1, "Onboarding & Intelligence", "Builds and analyzes the site's internal link graph", "agents.layer1.link_graph"),
    AgentEntry(23, "SiteHealthScoringAgent", 1, "Onboarding & Intelligence", "Produces an overall site health score from crawl data", "agents.layer1.health_scoring"),
    AgentEntry(24, "CrawlEvidenceAgent", 1, "Onboarding & Intelligence", "Collects and stores raw crawl evidence for recommendations", "agents.layer1.crawl_evidence"),
    AgentEntry(25, "ScreenshotCaptureAgent", 1, "Onboarding & Intelligence", "Captures and stores page screenshots via Playwright", "agents.layer1.screenshot"),

    # ── LAYER 2: Product/Market Understanding ───────────────────────────────
    AgentEntry(26, "ProductUnderstandingAgent", 2, "Product Understanding", "Synthesizes product summary from crawled content", "agents.layer2.product_understanding"),
    AgentEntry(27, "ProductCategoryAgent", 2, "Product Understanding", "Infers product category and subcategory", "agents.layer2.product_category"),
    AgentEntry(28, "ValuePropExtractionAgent", 2, "Product Understanding", "Extracts stated and inferred value propositions", "agents.layer2.value_prop"),
    AgentEntry(29, "PricingSignalAgent", 2, "Product Understanding", "Detects pricing model signals from content", "agents.layer2.pricing_signal"),
    AgentEntry(30, "ICPInferenceAgent", 2, "Product Understanding", "Infers Ideal Customer Profiles from content signals", "agents.layer2.icp_inference"),
    AgentEntry(31, "PersonaInferenceAgent", 2, "Product Understanding", "Drafts buyer personas from ICP signals", "agents.layer2.persona_inference"),
    AgentEntry(32, "JTBDExtractionAgent", 2, "Product Understanding", "Extracts Jobs-to-be-Done from content and use cases", "agents.layer2.jtbd"),
    AgentEntry(33, "ObjectionInferenceAgent", 2, "Product Understanding", "Infers likely buyer objections and concerns", "agents.layer2.objection_inference"),
    AgentEntry(34, "TrustSignalInferenceAgent", 2, "Product Understanding", "Identifies trust signals: logos, testimonials, certs", "agents.layer2.trust_signals"),
    AgentEntry(35, "MessagingFrameworkAgent", 2, "Product Understanding", "Drafts a messaging framework structure", "agents.layer2.messaging_framework"),
    AgentEntry(36, "PositioningDraftAgent", 2, "Product Understanding", "Generates a positioning statement draft", "agents.layer2.positioning_draft"),
    AgentEntry(37, "OfferAnalysisAgent", 2, "Product Understanding", "Analyzes offer structure: features, benefits, outcomes", "agents.layer2.offer_analysis"),

    # ── LAYER 3: Competitor/Category Intel ──────────────────────────────────
    AgentEntry(38, "CompetitorDiscoveryAgent", 3, "Competitor Intel", "Discovers direct and indirect competitors", "agents.layer3.competitor_discovery"),
    AgentEntry(39, "CompetitorClusteringAgent", 3, "Competitor Intel", "Clusters competitors into categories", "agents.layer3.competitor_clustering"),
    AgentEntry(40, "DirectVsIndirectCompetitorAgent", 3, "Competitor Intel", "Classifies competitors as direct vs. indirect", "agents.layer3.direct_vs_indirect"),
    AgentEntry(41, "AlternativeSolutionMapAgent", 3, "Competitor Intel", "Maps alternative solutions in the category", "agents.layer3.alternatives_map"),
    AgentEntry(42, "CompetitorMessagingAgent", 3, "Competitor Intel", "Analyzes competitor messaging and positioning", "agents.layer3.competitor_messaging"),
    AgentEntry(43, "CompetitorFeatureMatrixAgent", 3, "Competitor Intel", "Builds feature comparison matrix", "agents.layer3.feature_matrix"),
    AgentEntry(44, "CompetitorContentPatternAgent", 3, "Competitor Intel", "Identifies competitor content patterns and themes", "agents.layer3.content_patterns"),
    AgentEntry(45, "BattlecardAgent", 3, "Competitor Intel", "Generates sales battlecards per competitor", "agents.layer3.battlecard"),
    AgentEntry(46, "ComparisonNarrativeAgent", 3, "Competitor Intel", "Drafts 'us vs them' comparison narratives", "agents.layer3.comparison_narrative"),
    AgentEntry(47, "CategoryLandscapeAgent", 3, "Competitor Intel", "Maps the full category landscape", "agents.layer3.category_landscape"),

    # ── LAYER 4: Search Growth ───────────────────────────────────────────────
    AgentEntry(48, "TechnicalSEOAuditAgent", 4, "SEO", "Audits technical SEO: crawlability, speed, indexation", "agents.layer4.technical_seo"),
    AgentEntry(49, "OnPageSEOAuditAgent", 4, "SEO", "Audits on-page SEO: title, description, headings, content", "agents.layer4.onpage_seo"),
    AgentEntry(50, "InternalLinkingStrategyAgent", 4, "SEO", "Recommends internal linking improvements", "agents.layer4.internal_linking"),
    AgentEntry(51, "InformationArchitectureAgent", 4, "SEO", "Recommends IA improvements for site structure", "agents.layer4.ia"),
    AgentEntry(52, "TopicClusterAgent", 4, "SEO", "Proposes topic cluster architecture", "agents.layer4.topic_clusters"),
    AgentEntry(53, "ContentGapAgent", 4, "SEO", "Identifies content gaps vs. competitors and search demand", "agents.layer4.content_gap"),
    AgentEntry(54, "PageRefreshOpportunityAgent", 4, "SEO", "Identifies pages that need content refresh", "agents.layer4.page_refresh"),
    AgentEntry(55, "FAQOpportunityAgent", 4, "SEO", "Identifies FAQ content opportunities", "agents.layer4.faq_opportunities"),
    AgentEntry(56, "GlossaryOpportunityAgent", 4, "SEO", "Identifies glossary/definition page opportunities", "agents.layer4.glossary"),
    AgentEntry(57, "SchemaOpportunityAgent", 4, "SEO", "Identifies structured data schema opportunities", "agents.layer4.schema_opportunities"),
    AgentEntry(58, "CTRImprovementAgent", 4, "SEO", "Suggests title and meta improvements for CTR", "agents.layer4.ctr_improvement"),
    AgentEntry(59, "RecommendationPrioritizationAgent", 4, "SEO", "Scores and prioritizes SEO recommendations", "agents.layer4.rec_prioritization"),
    AgentEntry(60, "SearchBacklogBuilderAgent", 4, "SEO", "Assembles prioritized search growth backlog", "agents.layer4.search_backlog"),

    # ── LAYER 5: GEO/AEO/AI Visibility ──────────────────────────────────────
    AgentEntry(61, "AIVisibilityAgent", 5, "GEO/AEO", "Overall AI visibility assessment (experimental)", "agents.layer5.ai_visibility"),
    AgentEntry(62, "CitationReadinessAgent", 5, "GEO/AEO", "Evaluates readiness to be cited by LLMs", "agents.layer5.citation_readiness"),
    AgentEntry(63, "AnswerSurfaceCoverageAgent", 5, "GEO/AEO", "Evaluates coverage of answer-surface query types", "agents.layer5.answer_coverage"),
    AgentEntry(64, "CategoryRecommendationLikelihoodAgent", 5, "GEO/AEO", "Estimates likelihood of category recommendation by AI", "agents.layer5.category_recommendation"),
    AgentEntry(65, "BrandEntityConsistencyAgent", 5, "GEO/AEO", "Checks brand entity consistency across web", "agents.layer5.entity_consistency"),
    AgentEntry(66, "SourceabilityImprovementAgent", 5, "GEO/AEO", "Recommends improvements for LLM sourceability", "agents.layer5.sourceability"),
    AgentEntry(67, "UseCaseCoverageAgent", 5, "GEO/AEO", "Evaluates use case page coverage for AI discoverability", "agents.layer5.use_case_coverage"),
    AgentEntry(68, "ComparisonCoverageAgent", 5, "GEO/AEO", "Evaluates comparison page coverage", "agents.layer5.comparison_coverage"),
    AgentEntry(69, "FAQCoverageAgent", 5, "GEO/AEO", "Evaluates FAQ coverage for AI answer surfaces", "agents.layer5.faq_coverage"),
    AgentEntry(70, "AIVisibilityBacklogAgent", 5, "GEO/AEO", "Assembles AI visibility improvement backlog", "agents.layer5.visibility_backlog"),

    # ── LAYER 6: Analytics/Attribution ──────────────────────────────────────
    AgentEntry(71, "SearchConsoleIngestionAgent", 6, "Analytics", "Ingests Google Search Console data", "agents.layer6.gsc_ingestion"),
    AgentEntry(72, "GA4IngestionAgent", 6, "Analytics", "Ingests GA4 data", "agents.layer6.ga4_ingestion"),
    AgentEntry(73, "KPIAggregationAgent", 6, "Analytics", "Aggregates KPIs across sources", "agents.layer6.kpi_aggregation"),
    AgentEntry(74, "TrendAnalysisAgent", 6, "Analytics", "Identifies trends and period-over-period deltas", "agents.layer6.trends"),
    AgentEntry(75, "AnomalyDetectionAgent", 6, "Analytics", "Detects anomalies in traffic and conversion data", "agents.layer6.anomalies"),
    AgentEntry(76, "LandingPagePerformanceAgent", 6, "Analytics", "Analyzes landing page performance metrics", "agents.layer6.landing_pages"),
    AgentEntry(77, "QueryOpportunityAgent", 6, "Analytics", "Identifies search query opportunities from GSC data", "agents.layer6.query_opportunities"),
    AgentEntry(78, "ContentPerformanceAgent", 6, "Analytics", "Scores content assets by performance signals", "agents.layer6.content_performance"),
    AgentEntry(79, "ChannelAttributionAgent", 6, "Analytics", "Summarizes channel attribution", "agents.layer6.channel_attribution"),
    AgentEntry(80, "FunnelSummaryAgent", 6, "Analytics", "Produces funnel conversion summaries", "agents.layer6.funnel_summary"),
    AgentEntry(81, "MetricsNarrativeAgent", 6, "Analytics", "Writes human-readable narrative of metrics", "agents.layer6.metrics_narrative"),

    # ── LAYER 7: Content Strategy ────────────────────────────────────────────
    AgentEntry(82, "ContentStrategyAgent", 7, "Content Strategy", "Produces overall content strategy recommendations", "agents.layer7.content_strategy"),
    AgentEntry(83, "EditorialCalendarAgent", 7, "Content Strategy", "Generates editorial calendar suggestions", "agents.layer7.editorial_calendar"),
    AgentEntry(84, "ContentBriefAgent", 7, "Content Strategy", "Generates detailed content briefs", "agents.layer7.content_brief"),
    AgentEntry(85, "BlogBriefAgent", 7, "Content Strategy", "Specialised blog post brief generator", "agents.layer7.blog_brief"),
    AgentEntry(86, "ComparisonPageBriefAgent", 7, "Content Strategy", "Generates comparison page briefs", "agents.layer7.comparison_brief"),
    AgentEntry(87, "LandingPageVariantAgent", 7, "Content Strategy", "Suggests landing page copy variants", "agents.layer7.landing_variants"),
    AgentEntry(88, "FAQDraftAgent", 7, "Content Strategy", "Drafts FAQ content", "agents.layer7.faq_draft"),
    AgentEntry(89, "NewsletterAngleAgent", 7, "Content Strategy", "Generates newsletter angle and hooks", "agents.layer7.newsletter_angle"),
    AgentEntry(90, "OfferMessagingVariantAgent", 7, "Content Strategy", "Generates offer messaging variants", "agents.layer7.offer_messaging"),
    AgentEntry(91, "AudienceIntentMappingAgent", 7, "Content Strategy", "Maps content to audience intent stages", "agents.layer7.intent_mapping"),

    # ── LAYER 8: Content Production ──────────────────────────────────────────
    AgentEntry(92, "LongFormWriterAgent", 8, "Content Production", "Writes long-form blog and guide content", "agents.layer8.longform_writer"),
    AgentEntry(93, "LandingPageCopyAgent", 8, "Content Production", "Writes landing page copy", "agents.layer8.landing_copy"),
    AgentEntry(94, "SocialPostWriterAgent", 8, "Content Production", "Writes generic social posts", "agents.layer8.social_writer"),
    AgentEntry(95, "RedditPostDraftAgent", 8, "Content Production", "Drafts Reddit posts (human review required)", "agents.layer8.reddit_draft"),
    AgentEntry(96, "LinkedInPostDraftAgent", 8, "Content Production", "Drafts LinkedIn posts", "agents.layer8.linkedin_draft"),
    AgentEntry(97, "XThreadDraftAgent", 8, "Content Production", "Drafts X/Twitter threads", "agents.layer8.x_thread"),
    AgentEntry(98, "ProductHuntCopyAgent", 8, "Content Production", "Drafts Product Hunt listing copy", "agents.layer8.product_hunt"),
    AgentEntry(99, "OutreachEmailAgent", 8, "Content Production", "Drafts outreach email templates", "agents.layer8.outreach_email"),
    AgentEntry(100, "ContentEditorAgent", 8, "Content Production", "Edits and improves draft content", "agents.layer8.content_editor"),
    AgentEntry(101, "ToneConsistencyAgent", 8, "Content Production", "Checks and adjusts tone consistency", "agents.layer8.tone_consistency"),
    AgentEntry(102, "ClaimEvidenceAgent", 8, "Content Production", "Verifies claims have adequate evidence", "agents.layer8.claim_evidence"),
    AgentEntry(103, "ContentScoringAgent", 8, "Content Production", "Scores content quality along multiple dimensions", "agents.layer8.content_scoring"),
    AgentEntry(104, "ContentRevisionAgent", 8, "Content Production", "Applies revision instructions to content", "agents.layer8.content_revision"),

    # ── LAYER 9: Distribution & Operations ───────────────────────────────────
    AgentEntry(105, "DistributionPlannerAgent", 9, "Distribution", "Creates channel distribution plans", "agents.layer9.distribution_planner"),
    AgentEntry(106, "ChannelFitScoringAgent", 9, "Distribution", "Scores content-channel fit", "agents.layer9.channel_fit"),
    AgentEntry(107, "PublishPackageAgent", 9, "Distribution", "Assembles publish-ready content packages", "agents.layer9.publish_package"),
    AgentEntry(108, "CMSPublishPreparationAgent", 9, "Distribution", "Prepares content for CMS publishing", "agents.layer9.cms_prep"),
    AgentEntry(109, "SocialSchedulePreparationAgent", 9, "Distribution", "Prepares social posts for scheduling", "agents.layer9.social_schedule"),
    AgentEntry(110, "ApprovalQueueRoutingAgent", 9, "Distribution", "Routes items to appropriate approval queues", "agents.layer9.approval_routing"),
    AgentEntry(111, "LowRiskAutomationAgent", 9, "Distribution", "Executes pre-approved low-risk actions autonomously", "agents.layer9.low_risk_automation"),
    AgentEntry(112, "NotificationAgent", 9, "Distribution", "Sends notifications via Slack/email", "agents.layer9.notification"),
    AgentEntry(113, "CampaignAssemblyAgent", 9, "Distribution", "Assembles multi-channel campaigns", "agents.layer9.campaign_assembly"),

    # ── LAYER 10: Experimentation ────────────────────────────────────────────
    AgentEntry(114, "ExperimentDesignerAgent", 10, "Experimentation", "Designs structured A/B experiments", "agents.layer10.experiment_designer"),
    AgentEntry(115, "HypothesisAgent", 10, "Experimentation", "Formulates testable hypotheses", "agents.layer10.hypothesis"),
    AgentEntry(116, "VariantGenerationAgent", 10, "Experimentation", "Generates copy/content variants for testing", "agents.layer10.variant_generation"),
    AgentEntry(117, "SuccessMetricAgent", 10, "Experimentation", "Defines success metrics for experiments", "agents.layer10.success_metrics"),
    AgentEntry(118, "ExperimentPrioritizationAgent", 10, "Experimentation", "Prioritizes experiment backlog by expected value", "agents.layer10.experiment_prioritization"),
    AgentEntry(119, "ExperimentReviewAgent", 10, "Experimentation", "Reviews completed experiment results", "agents.layer10.experiment_review"),
    AgentEntry(120, "ExperimentSummaryAgent", 10, "Experimentation", "Summarizes experiment outcomes and learnings", "agents.layer10.experiment_summary"),

    # ── LAYER 11: Reporting/Executive ────────────────────────────────────────
    AgentEntry(121, "DailySummaryAgent", 11, "Reporting", "Generates daily growth summary", "agents.layer11.daily_summary"),
    AgentEntry(122, "WeeklyReportAgent", 11, "Reporting", "Generates weekly growth report", "agents.layer11.weekly_report"),
    AgentEntry(123, "MonthlyExecutiveSummaryAgent", 11, "Reporting", "Generates monthly executive summary", "agents.layer11.monthly_summary"),
    AgentEntry(124, "OpportunityDigestAgent", 11, "Reporting", "Digests top opportunities across all systems", "agents.layer11.opportunity_digest"),
    AgentEntry(125, "RiskDigestAgent", 11, "Reporting", "Digests top risks and blockers", "agents.layer11.risk_digest"),
    AgentEntry(126, "WhatChangedAgent", 11, "Reporting", "Summarizes what changed since last report", "agents.layer11.what_changed"),
    AgentEntry(127, "NextActionsAgent", 11, "Reporting", "Generates prioritized next action list", "agents.layer11.next_actions"),
    AgentEntry(128, "NarrativeSynthesisAgent", 11, "Reporting", "Synthesizes all signals into cohesive narrative", "agents.layer11.narrative_synthesis"),

    # ── LAYER 12: Quality/Evaluation ────────────────────────────────────────
    AgentEntry(129, "PromptEvaluationAgent", 12, "Quality", "Runs regression tests on prompts", "agents.layer12.prompt_eval"),
    AgentEntry(130, "RecommendationQualityAgent", 12, "Quality", "Checks recommendation quality and evidence", "agents.layer12.rec_quality"),
    AgentEntry(131, "ContentQualityAgent", 12, "Quality", "Checks content quality along defined rubric", "agents.layer12.content_quality"),
    AgentEntry(132, "ToolReliabilityAgent", 12, "Quality", "Tests tool reliability and correctness", "agents.layer12.tool_reliability"),
    AgentEntry(133, "WorkflowRegressionAgent", 12, "Quality", "Runs workflow regression tests", "agents.layer12.workflow_regression"),
    AgentEntry(134, "HallucinationRiskAgent", 12, "Quality", "Flags potential hallucination risks in outputs", "agents.layer12.hallucination_risk"),
    AgentEntry(135, "SchemaValidationAgent", 12, "Quality", "Validates all structured outputs against schemas", "agents.layer12.schema_validation"),
    AgentEntry(136, "OutputCriticAgent", 12, "Quality", "Critiques agent outputs for improvement", "agents.layer12.output_critic"),
    AgentEntry(137, "SelfReviewAgent", 12, "Quality", "Agents review their own outputs", "agents.layer12.self_review"),
    AgentEntry(138, "ReleaseReadinessAgent", 12, "Quality", "Checks system readiness for production changes", "agents.layer12.release_readiness"),
]

# Lookup helpers
REGISTRY_BY_NAME: dict[str, AgentEntry] = {a.name: a for a in AGENT_REGISTRY}
REGISTRY_BY_LAYER: dict[int, list[AgentEntry]] = {}
for agent in AGENT_REGISTRY:
    REGISTRY_BY_LAYER.setdefault(agent.layer, []).append(agent)


def get_agent(name: str) -> AgentEntry | None:
    return REGISTRY_BY_NAME.get(name)


def get_agents_for_layer(layer: int) -> list[AgentEntry]:
    return REGISTRY_BY_LAYER.get(layer, [])


def get_all_agent_names() -> list[str]:
    return [a.name for a in AGENT_REGISTRY]
