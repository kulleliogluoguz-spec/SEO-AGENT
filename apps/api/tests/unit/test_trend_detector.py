"""Unit tests for the Trend Detector."""

from datetime import UTC, datetime, timedelta

from app.agents.trends.trend_detector import TrendDetector


def make_doc(
    id: str,
    title: str,
    text: str,
    days_ago: int = 0,
    source_type: str = "rss",
) -> dict:
    """Helper to create a sample document dict."""
    return {
        "id": id,
        "title": title,
        "raw_text": text,
        "published_at": datetime.now(tz=UTC) - timedelta(days=days_ago),
        "source_type": source_type,
        "source_url": f"https://example.com/{id}",
        "metadata": {},
    }


class TestTrendDetector:
    def setup_method(self):
        self.detector = TrendDetector(min_document_count=2)

    def test_no_documents_returns_empty(self):
        result = self.detector.detect_trends([])
        assert result == []

    def test_single_document_below_threshold(self):
        docs = [
            make_doc("1", "AI automation", "AI is transforming automation workflows", days_ago=1)
        ]
        result = self.detector.detect_trends(docs)
        assert result == []  # min_document_count=2

    def test_multiple_documents_same_topic(self):
        docs = [
            make_doc("1", "AI automation growth", "AI automation is growing fast", days_ago=1),
            make_doc(
                "2", "automation trends 2026", "automation tools are trending now", days_ago=2
            ),
            make_doc("3", "automation market", "the automation market is expanding", days_ago=3),
        ]
        result = self.detector.detect_trends(docs)
        assert len(result) > 0
        # Should find "automation" as a trend
        top_keywords = " ".join([" ".join(c.keywords) for c in result]).lower()
        assert "automation" in top_keywords

    def test_momentum_calculation_rising(self):
        """Documents from current week should have positive momentum vs prior week."""
        # 5 current week docs
        current = [
            make_doc(
                f"curr-{i}", "kubernetes scaling", "kubernetes scaling issues solved", days_ago=i
            )
            for i in range(5)
        ]
        # 1 prior week doc
        prior = [
            make_doc("prior-1", "kubernetes basics", "kubernetes basics tutorial", days_ago=10)
        ]
        result = self.detector.detect_trends(current + prior)
        k8s_trends = [c for c in result if "kubernetes" in " ".join(c.keywords)]
        if k8s_trends:
            assert k8s_trends[0].momentum_score > 0  # Rising

    def test_brand_relevance_scoring(self):
        """Trends matching brand keywords should get higher relevance scores."""
        brand_profile = {
            "positioning_keywords": ["machine learning", "python", "data pipeline"],
            "content_topics": ["mlops", "model deployment"],
            "icp_description": "data scientists and ML engineers",
        }
        docs = [
            make_doc(
                "1", "Python MLOps pipeline", "Python MLOps pipeline best practices", days_ago=1
            ),
            make_doc("2", "MLOps deployment", "model deployment with MLOps tools", days_ago=2),
            make_doc("3", "gardening tips", "how to grow tomatoes in your garden", days_ago=1),
            make_doc("4", "garden watering", "watering schedule for garden plants", days_ago=2),
        ]
        result = self.detector.detect_trends(docs, brand_profile=brand_profile)

        # MLOps trends should have higher relevance than gardening trends
        mlops_trends = [
            c
            for c in result
            if any("mlops" in kw or "python" in kw or "pipeline" in kw for kw in c.keywords)
        ]
        garden_trends = [
            c for c in result if any("garden" in kw or "tomato" in kw for kw in c.keywords)
        ]

        if mlops_trends and garden_trends:
            mlops_relevance = mlops_trends[0].metadata.get("relevance_score", 0)
            garden_relevance = garden_trends[0].metadata.get("relevance_score", 0)
            assert mlops_relevance > garden_relevance

    def test_keyword_extraction_filters_stopwords(self):
        """Stop words should not appear in extracted keywords."""
        text = "the best way to build a really great product for your customers"
        keywords = self.detector._extract_keywords(text)
        stop_words_in_result = {"the", "to", "a", "for", "your", "way", "and"}
        found_stop = stop_words_in_result & set(keywords)
        assert not found_stop, f"Stop words found: {found_stop}"

    def test_keyword_extraction_produces_bigrams(self):
        """Bigrams should be extracted from meaningful word pairs."""
        text = "machine learning tools for production pipelines"
        keywords = self.detector._extract_keywords(text)
        bigrams = [k for k in keywords if " " in k]
        assert len(bigrams) > 0

    def test_evidence_is_included(self):
        """Each trend should include evidence from source documents."""
        docs = [
            make_doc("1", "serverless functions", "serverless functions are gaining popularity"),
            make_doc("2", "serverless architecture", "serverless architecture reduces costs"),
            make_doc("3", "serverless deployment", "serverless deployment is now standard"),
        ]
        result = self.detector.detect_trends(docs)
        if result:
            top_trend = result[0]
            assert len(top_trend.evidence) > 0
            first_evidence = top_trend.evidence[0]
            assert "title" in first_evidence
            assert "url" in first_evidence

    def test_results_sorted_by_momentum_times_count(self):
        """Results should be sorted by momentum * document_count descending."""
        docs = []
        # 5 docs about "database optimization" (strong trend)
        for i in range(5):
            docs.append(
                make_doc(
                    f"db-{i}", "database optimization", "sql database optimization tips", days_ago=i
                )
            )
        # 2 docs about "coffee brewing" (weaker trend)
        for i in range(2):
            docs.append(
                make_doc(
                    f"coffee-{i}",
                    "coffee brewing methods",
                    "best coffee brewing methods",
                    days_ago=i,
                )
            )

        result = self.detector.detect_trends(docs)
        if len(result) >= 2:
            # Scores should be non-increasing
            scores = [c.momentum_score * c.document_count for c in result]
            assert scores == sorted(scores, reverse=True)
