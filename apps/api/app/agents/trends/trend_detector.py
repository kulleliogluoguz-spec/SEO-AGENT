"""
Trend Detector — Identifies rising topics from ingested source documents.

Algorithm:
  1. For a given workspace, load recently ingested source_documents
  2. Extract keywords + noun phrases from each document (local NLP)
  3. Cluster documents by semantic similarity (Qdrant)
  4. Measure momentum: compare current window vs prior window
  5. Score relevance against the workspace's brand profile
  6. Emit TrendRecord objects for storage

All processing is local — no external API calls.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrendCandidate:
    """A candidate trend identified from document analysis."""
    title: str
    keywords: list[str]
    document_ids: list[str]
    document_count: int
    volume_7d: int
    volume_prior_7d: int
    momentum_score: float      # (current - prior) / max(prior, 1) — normalized
    sentiment_avg: float
    sources: list[str]
    evidence: list[dict]       # Sample excerpts with source URLs
    category: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_rising(self) -> bool:
        return self.momentum_score > 0.2

    @property
    def is_strong(self) -> bool:
        return self.document_count >= 3 and self.momentum_score > 0.0


@dataclass
class TrendRelevanceScore:
    """Relevance of a trend candidate to a brand profile."""
    trend_title: str
    relevance_score: float     # 0-1
    matching_keywords: list[str]
    reasoning: str


class TrendDetector:
    """
    Detects rising trends from ingested source documents.

    Uses keyword extraction + frequency analysis for the core algorithm.
    Optionally enriched by semantic clustering via Qdrant.
    """

    def __init__(
        self,
        min_document_count: int = 2,
        momentum_window_days: int = 7,
        min_momentum_score: float = 0.0,
    ) -> None:
        self.min_document_count = min_document_count
        self.momentum_window_days = momentum_window_days
        self.min_momentum_score = min_momentum_score

    def detect_trends(
        self,
        documents: list[dict],      # List of source_document dicts
        brand_profile: Optional[dict] = None,
    ) -> list[TrendCandidate]:
        """
        Detect trend candidates from a list of source documents.

        Args:
            documents: List of document dicts with keys:
                id, title, raw_text, published_at, source_type, source_url, metadata
            brand_profile: Optional brand profile for relevance scoring

        Returns:
            List of TrendCandidate objects sorted by momentum_score descending
        """
        if not documents:
            return []

        now = datetime.now(tz=timezone.utc)
        window_start = now - timedelta(days=self.momentum_window_days)
        prior_window_start = window_start - timedelta(days=self.momentum_window_days)

        # Split documents into current vs prior window
        current_docs = [
            d for d in documents
            if self._parse_date(d.get("published_at")) and
               self._parse_date(d.get("published_at")) >= window_start
        ]
        prior_docs = [
            d for d in documents
            if self._parse_date(d.get("published_at")) and
               prior_window_start <= self._parse_date(d.get("published_at")) < window_start
        ]

        # Extract keyword frequencies for each window
        current_kw_freq = self._extract_keyword_frequencies(current_docs)
        prior_kw_freq = self._extract_keyword_frequencies(prior_docs)

        # Build trend candidates from current keyword clusters
        candidates = self._build_candidates(
            current_docs, current_kw_freq, prior_kw_freq
        )

        # Filter and sort
        candidates = [c for c in candidates if c.document_count >= self.min_document_count]
        candidates = [c for c in candidates if c.momentum_score >= self.min_momentum_score]
        candidates.sort(key=lambda c: c.momentum_score * c.document_count, reverse=True)

        # Score relevance against brand profile if available
        if brand_profile:
            candidates = self._score_brand_relevance(candidates, brand_profile)

        return candidates

    def _extract_keyword_frequencies(self, documents: list[dict]) -> Counter:
        """Extract keyword frequencies from a list of documents."""
        all_keywords: list[str] = []

        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('raw_text', '')}"
            keywords = self._extract_keywords(text)
            all_keywords.extend(keywords)

        return Counter(all_keywords)

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Simple keyword extraction using heuristics.
        Returns meaningful noun phrases and important terms.
        """
        if not text:
            return []

        # Normalize text
        text = text.lower()
        text = re.sub(r"[^\w\s-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Stop words to filter
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "this", "that",
            "these", "those", "i", "you", "he", "she", "it", "we", "they",
            "what", "which", "who", "when", "where", "why", "how",
            "not", "no", "nor", "so", "yet", "both", "either", "neither",
            "just", "also", "than", "then", "there", "here", "very",
        }

        words = text.split()
        keywords = []

        # Single meaningful words (length > 3, not stop words)
        for word in words:
            word = word.strip("-")
            if len(word) > 3 and word not in stop_words and word.isalpha():
                keywords.append(word)

        # Bigrams (two-word phrases)
        for i in range(len(words) - 1):
            w1, w2 = words[i].strip("-"), words[i + 1].strip("-")
            if (
                w1 not in stop_words and w2 not in stop_words
                and len(w1) > 2 and len(w2) > 2
                and w1.isalpha() and w2.isalpha()
            ):
                keywords.append(f"{w1} {w2}")

        return keywords

    def _build_candidates(
        self,
        current_docs: list[dict],
        current_kw_freq: Counter,
        prior_kw_freq: Counter,
    ) -> list[TrendCandidate]:
        """Build TrendCandidate objects from keyword clusters."""
        candidates = []

        # Use top keywords as cluster seeds
        top_keywords = [kw for kw, _ in current_kw_freq.most_common(50)]

        # For each top keyword, gather related documents
        seen_clusters: set[frozenset] = set()

        for keyword in top_keywords:
            # Find docs containing this keyword
            related_docs = [
                d for d in current_docs
                if keyword in self._extract_keywords(
                    f"{d.get('title', '')} {d.get('raw_text', '')}"
                )
            ]

            if len(related_docs) < self.min_document_count:
                continue

            # Deduplicate: skip if this cluster overlaps significantly with an existing one
            cluster_ids = frozenset(d["id"] for d in related_docs)
            is_duplicate = any(
                len(cluster_ids & seen) / max(len(cluster_ids), 1) > 0.8
                for seen in seen_clusters
            )
            if is_duplicate:
                continue
            seen_clusters.add(cluster_ids)

            # Calculate momentum
            current_count = current_kw_freq.get(keyword, 0)
            prior_count = prior_kw_freq.get(keyword, 0)
            momentum = (current_count - prior_count) / max(prior_count, 1)
            momentum = max(-1.0, min(2.0, momentum))  # Clamp to reasonable range

            # Gather co-occurring keywords
            all_text = " ".join(
                f"{d.get('title', '')} {d.get('raw_text', '')[:500]}"
                for d in related_docs
            )
            co_keywords = self._extract_keywords(all_text)
            co_freq = Counter(co_keywords).most_common(10)
            cluster_keywords = [keyword] + [kw for kw, _ in co_freq if kw != keyword][:5]

            # Build evidence (sample excerpts)
            evidence = []
            for doc in related_docs[:3]:
                excerpt = (doc.get("raw_text", "") or "")[:200].strip()
                if excerpt:
                    evidence.append({
                        "title": doc.get("title", ""),
                        "excerpt": excerpt,
                        "url": doc.get("source_url", ""),
                        "source_type": doc.get("source_type", ""),
                        "published_at": str(doc.get("published_at", "")),
                    })

            candidates.append(TrendCandidate(
                title=keyword.title(),
                keywords=cluster_keywords,
                document_ids=[d["id"] for d in related_docs],
                document_count=len(related_docs),
                volume_7d=current_count,
                volume_prior_7d=prior_count,
                momentum_score=round(momentum, 3),
                sentiment_avg=0.0,  # TODO: add sentiment analysis
                sources=list({d.get("source_type", "unknown") for d in related_docs}),
                evidence=evidence,
            ))

        return candidates

    def _score_brand_relevance(
        self,
        candidates: list[TrendCandidate],
        brand_profile: dict,
    ) -> list[TrendCandidate]:
        """
        Score each trend candidate's relevance to the brand profile.
        Sets metadata["relevance_score"] and metadata["matching_keywords"].

        Uses simple keyword overlap scoring. Can be enhanced with
        semantic similarity via embeddings in future iterations.
        """
        brand_keywords = set()

        # Extract brand keywords from profile
        for field in ["positioning_keywords", "content_topics", "product_features"]:
            values = brand_profile.get(field, [])
            if isinstance(values, list):
                for v in values:
                    if isinstance(v, str):
                        brand_keywords.update(v.lower().split())
                    elif isinstance(v, dict):
                        brand_keywords.update(str(v).lower().split())

        icp = brand_profile.get("icp_description", "")
        if icp:
            brand_keywords.update(icp.lower().split())

        if not brand_keywords:
            return candidates

        for candidate in candidates:
            trend_keywords = set(" ".join(candidate.keywords).lower().split())
            matching = brand_keywords & trend_keywords
            relevance = len(matching) / max(len(trend_keywords), 1)
            relevance = min(relevance * 3, 1.0)  # Scale up — exact matches are very relevant

            candidate.metadata["relevance_score"] = round(relevance, 3)
            candidate.metadata["matching_keywords"] = list(matching)

        return candidates

    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse a date value to timezone-aware datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None
        return None
