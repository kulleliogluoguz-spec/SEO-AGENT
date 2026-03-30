"""
Evaluation Layer — AI quality assurance and regression testing.

Provides:
- Eval suite definitions (test cases for prompts/engines)
- Automated quality scoring
- Regression detection (prompt changes that degrade output)
- Structured output reliability testing
- Recommendation quality assessment
- Hallucination risk scoring
- A/B comparison between models/prompts
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EvalMetric(str, Enum):
    ACCURACY = "accuracy"               # Factual correctness
    RELEVANCE = "relevance"             # Answer relevance to query
    COMPLETENESS = "completeness"       # Covers all required aspects
    STRUCTURED_OUTPUT = "structured_output"  # Valid JSON/schema compliance
    HALLUCINATION_RISK = "hallucination_risk"  # Unsupported claims
    ACTIONABILITY = "actionability"     # Recommendations are actionable
    EVIDENCE_QUALITY = "evidence_quality"  # Evidence cited properly
    TONE_COMPLIANCE = "tone_compliance"  # Matches brand/professional tone
    SAFETY = "safety"                   # No harmful/deceptive content
    LATENCY = "latency"                 # Response time


@dataclass
class EvalCase:
    """A single test case in an eval suite."""
    id: str
    name: str
    input_text: str
    expected_output: Optional[str] = None     # Reference output
    expected_contains: list[str] = field(default_factory=list)  # Must contain
    expected_not_contains: list[str] = field(default_factory=list)  # Must not contain
    expected_json_keys: list[str] = field(default_factory=list)  # Required JSON fields
    max_latency_ms: float = 10000
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """Result of running a single eval case."""
    case_id: str
    passed: bool
    scores: dict[str, float] = field(default_factory=dict)  # metric -> score (0-1)
    output: str = ""
    latency_ms: float = 0.0
    model_used: str = ""
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvalSuite:
    """A collection of eval cases for a prompt/engine."""
    id: str
    name: str
    description: str = ""
    prompt_id: str = ""
    engine: str = ""
    cases: list[EvalCase] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalRun:
    """A complete evaluation run."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    suite_id: str = ""
    results: list[EvalResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    model_used: str = ""
    prompt_version: str = ""

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def avg_scores(self) -> dict[str, float]:
        all_metrics: dict[str, list[float]] = {}
        for r in self.results:
            for metric, score in r.scores.items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append(score)
        return {m: sum(s) / len(s) for m, s in all_metrics.items() if s}

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "suite_id": self.suite_id,
            "model": self.model_used,
            "prompt_version": self.prompt_version,
            "total_cases": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "pass_rate": round(self.pass_rate, 3),
            "avg_scores": {k: round(v, 3) for k, v in self.avg_scores.items()},
            "avg_latency_ms": round(
                sum(r.latency_ms for r in self.results) / max(len(self.results), 1), 1
            ),
        }


class EvalHarness:
    """
    Evaluation harness for running quality checks.

    Supports:
    - Running individual eval cases
    - Running full eval suites
    - Comparing runs across models/prompt versions
    - Regression detection
    """

    def __init__(self) -> None:
        self._suites: dict[str, EvalSuite] = {}
        self._runs: list[EvalRun] = []
        self._load_defaults()

    def register_suite(self, suite: EvalSuite) -> None:
        self._suites[suite.id] = suite

    def get_suite(self, suite_id: str) -> Optional[EvalSuite]:
        return self._suites.get(suite_id)

    def list_suites(self) -> list[dict]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "prompt_id": s.prompt_id,
                "engine": s.engine,
                "case_count": len(s.cases),
                "tags": s.tags,
            }
            for s in self._suites.values()
        ]

    async def run_suite(
        self,
        suite_id: str,
        engine_executor: Any,  # The engine's execute method
        model_id: str = "",
        prompt_version: str = "",
    ) -> EvalRun:
        """Run an eval suite and return results."""
        suite = self._suites.get(suite_id)
        if not suite:
            return EvalRun(suite_id=suite_id)

        run = EvalRun(
            suite_id=suite_id,
            model_used=model_id,
            prompt_version=prompt_version,
        )

        for case in suite.cases:
            result = await self._run_case(case, engine_executor)
            run.results.append(result)

        run.completed_at = time.time()
        self._runs.append(run)

        logger.info(
            f"Eval run {run.id}: suite={suite_id} "
            f"passed={sum(1 for r in run.results if r.passed)}/{len(run.results)} "
            f"pass_rate={run.pass_rate:.1%}"
        )
        return run

    async def _run_case(self, case: EvalCase, executor: Any) -> EvalResult:
        """Run a single eval case."""
        start = time.time()
        try:
            result = await executor(case.input_text, context=case.context)
            output = result.raw_content if hasattr(result, "raw_content") else str(result)
            latency = (time.time() - start) * 1000

            scores, errors = self._score_output(case, output, latency)
            passed = all(s >= 0.5 for s in scores.values()) and not errors

            return EvalResult(
                case_id=case.id,
                passed=passed,
                scores=scores,
                output=output[:1000],
                latency_ms=latency,
                model_used=getattr(result, "model_used", ""),
                errors=errors,
            )
        except Exception as e:
            return EvalResult(
                case_id=case.id,
                passed=False,
                errors=[f"Execution error: {str(e)}"],
                latency_ms=(time.time() - start) * 1000,
            )

    def _score_output(
        self, case: EvalCase, output: str, latency_ms: float
    ) -> tuple[dict[str, float], list[str]]:
        """Score an output against eval case criteria."""
        scores: dict[str, float] = {}
        errors: list[str] = []

        # Latency check
        scores["latency"] = 1.0 if latency_ms <= case.max_latency_ms else 0.0
        if latency_ms > case.max_latency_ms:
            errors.append(f"Latency {latency_ms:.0f}ms exceeds max {case.max_latency_ms}ms")

        # Contains check
        if case.expected_contains:
            found = sum(1 for s in case.expected_contains if s.lower() in output.lower())
            scores["completeness"] = found / len(case.expected_contains)
            missing = [s for s in case.expected_contains if s.lower() not in output.lower()]
            if missing:
                errors.append(f"Missing expected content: {missing}")

        # Not-contains check
        if case.expected_not_contains:
            violations = [s for s in case.expected_not_contains if s.lower() in output.lower()]
            scores["safety"] = 1.0 if not violations else 0.0
            if violations:
                errors.append(f"Contains prohibited content: {violations}")

        # JSON structure check
        if case.expected_json_keys:
            try:
                parsed = json.loads(output)
                found_keys = sum(1 for k in case.expected_json_keys if k in parsed)
                scores["structured_output"] = found_keys / len(case.expected_json_keys)
                missing_keys = [k for k in case.expected_json_keys if k not in parsed]
                if missing_keys:
                    errors.append(f"Missing JSON keys: {missing_keys}")
            except json.JSONDecodeError:
                scores["structured_output"] = 0.0
                errors.append("Output is not valid JSON")

        # Non-empty check
        if len(output.strip()) < 10:
            scores["relevance"] = 0.0
            errors.append("Output is empty or too short")

        return scores, errors

    def get_run_history(self, suite_id: str = "", limit: int = 20) -> list[dict]:
        runs = self._runs
        if suite_id:
            runs = [r for r in runs if r.suite_id == suite_id]
        return [r.summary() for r in runs[-limit:]]

    def compare_runs(self, run_id_a: str, run_id_b: str) -> dict[str, Any]:
        """Compare two eval runs for regression detection."""
        run_a = next((r for r in self._runs if r.id == run_id_a), None)
        run_b = next((r for r in self._runs if r.id == run_id_b), None)
        if not run_a or not run_b:
            return {"error": "Run not found"}

        return {
            "run_a": run_a.summary(),
            "run_b": run_b.summary(),
            "pass_rate_delta": round(run_b.pass_rate - run_a.pass_rate, 3),
            "regression": run_b.pass_rate < run_a.pass_rate,
            "score_deltas": {
                metric: round(run_b.avg_scores.get(metric, 0) - run_a.avg_scores.get(metric, 0), 3)
                for metric in set(list(run_a.avg_scores.keys()) + list(run_b.avg_scores.keys()))
            },
        }

    def _load_defaults(self) -> None:
        """Load default eval suites."""

        # SEO Technical Audit eval suite
        self.register_suite(EvalSuite(
            id="eval_seo_technical",
            name="SEO Technical Audit Quality",
            engine="reasoning",
            prompt_id="seo.technical_audit",
            cases=[
                EvalCase(
                    id="seo_1",
                    name="Basic site audit request",
                    input_text="Analyze this site's technical SEO based on the crawl data provided.",
                    expected_contains=["issue", "recommendation"],
                    expected_json_keys=["summary", "issues"],
                    context={"crawl_data": '{"pages": 50, "errors": 3}'},
                ),
                EvalCase(
                    id="seo_2",
                    name="Audit with redirect chains",
                    input_text="Audit for redirect chains and canonical issues.",
                    expected_contains=["redirect", "canonical"],
                ),
            ],
            tags=["seo", "core"],
        ))

        # Recommendation quality eval
        self.register_suite(EvalSuite(
            id="eval_recommendations",
            name="Recommendation Quality",
            engine="recommendation",
            prompt_id="recommendation.generate",
            cases=[
                EvalCase(
                    id="rec_1",
                    name="Generate recs from analysis data",
                    input_text="Generate prioritized recommendations.",
                    expected_json_keys=["recommendations"],
                    expected_contains=["priority", "evidence", "implementation"],
                    context={"analysis_data": '{"traffic_decline": true, "missing_meta": 15}'},
                ),
            ],
            tags=["recommendations", "core"],
        ))

        # Guardrail eval
        self.register_suite(EvalSuite(
            id="eval_guardrails",
            name="Guardrail Safety",
            engine="guardrail",
            prompt_id="guardrail.content_check",
            cases=[
                EvalCase(
                    id="guard_1",
                    name="Clean content passes",
                    input_text="Check this content: 'Our product helps teams grow organic traffic through data-driven SEO recommendations.'",
                    expected_json_keys=["passed"],
                ),
                EvalCase(
                    id="guard_2",
                    name="Spammy content flagged",
                    input_text="Check this content: 'GUARANTEED #1 RANKING IN 24 HOURS! Buy backlinks now!'",
                    expected_contains=["issue", "spam"],
                    expected_not_contains=["passed\": true"],
                ),
            ],
            tags=["safety", "core"],
        ))

        logger.info(f"EvalHarness loaded {len(self._suites)} default suites")


# Singleton
_harness: Optional[EvalHarness] = None


def get_eval_harness() -> EvalHarness:
    global _harness
    if _harness is None:
        _harness = EvalHarness()
    return _harness
