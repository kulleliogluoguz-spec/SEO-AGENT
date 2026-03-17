"""Unit tests for WebCrawlerTool — SSRF protection and URL normalization."""
import pytest
from app.tools.web_crawler import WebCrawlerTool


class TestSSRFProtection:
    def setup_method(self):
        self.crawler = WebCrawlerTool()

    def test_localhost_is_blocked(self):
        assert self.crawler._is_blocked("http://localhost/admin") is True

    def test_loopback_ip_is_blocked(self):
        assert self.crawler._is_blocked("http://127.0.0.1/secret") is True

    def test_aws_metadata_is_blocked(self):
        assert self.crawler._is_blocked("http://169.254.169.254/latest/meta-data/") is True

    def test_public_domain_is_allowed(self):
        assert self.crawler._is_blocked("https://example.com") is False

    def test_public_ip_is_allowed(self):
        assert self.crawler._is_blocked("https://8.8.8.8") is False

    def test_private_ip_range_blocked(self):
        assert self.crawler._is_blocked("http://10.0.0.1/internal") is True
        assert self.crawler._is_blocked("http://192.168.1.1/router") is True
        assert self.crawler._is_blocked("http://172.16.0.1/internal") is True


class TestURLNormalization:
    def setup_method(self):
        self.crawler = WebCrawlerTool()

    def test_relative_url_resolved(self):
        result = self.crawler._normalize_url("/about", "https://example.com")
        assert result == "https://example.com/about"

    def test_absolute_url_unchanged(self):
        result = self.crawler._normalize_url("https://other.com/page", "https://example.com")
        assert result == "https://other.com/page"

    def test_fragment_stripped(self):
        result = self.crawler._normalize_url("/page#section", "https://example.com")
        assert result == "https://example.com/page"

    def test_javascript_scheme_rejected(self):
        result = self.crawler._normalize_url("javascript:void(0)", "https://example.com")
        assert result is None

    def test_mailto_scheme_rejected(self):
        result = self.crawler._normalize_url("mailto:user@example.com", "https://example.com")
        assert result is None


class TestPageExtraction:
    def setup_method(self):
        self.crawler = WebCrawlerTool()

    def test_extract_title(self):
        html = "<html><head><title>My Page Title</title></head><body><h1>Hello</h1></body></html>"
        page = self.crawler._extract_page_data("https://example.com", html, 200)
        assert page.title == "My Page Title"

    def test_extract_meta_description(self):
        html = '<html><head><meta name="description" content="Page description here"></head></html>'
        page = self.crawler._extract_page_data("https://example.com", html, 200)
        assert page.meta_description == "Page description here"

    def test_extract_h1(self):
        html = "<html><body><h1>Primary Heading</h1></body></html>"
        page = self.crawler._extract_page_data("https://example.com", html, 200)
        assert page.h1 == "Primary Heading"

    def test_missing_title_is_none(self):
        html = "<html><body><p>No title here</p></body></html>"
        page = self.crawler._extract_page_data("https://example.com", html, 200)
        assert page.title is None

    def test_word_count_calculated(self):
        html = "<html><body><p>One two three four five</p></body></html>"
        page = self.crawler._extract_page_data("https://example.com", html, 200)
        assert page.word_count >= 5

    def test_status_code_preserved(self):
        html = "<html><body></body></html>"
        page = self.crawler._extract_page_data("https://example.com", html, 404)
        assert page.status_code == 404

    def test_json_ld_extracted(self):
        html = '''<html><body>
            <script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
        </body></html>'''
        page = self.crawler._extract_page_data("https://example.com", html, 200)
        assert len(page.structured_data) == 1
        assert page.structured_data[0]["name"] == "Acme"

    def test_canonical_url_extracted(self):
        html = '<html><head><link rel="canonical" href="https://example.com/canonical"></head></html>'
        page = self.crawler._extract_page_data("https://example.com/old-url", html, 200)
        assert page.canonical_url == "https://example.com/canonical"
