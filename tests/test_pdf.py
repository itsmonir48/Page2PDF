"""
Page2PDF — PDF Generation Tests
Tests for PDF output.
"""
import pytest
import pytest_asyncio
from app.models.schemas import ExtractedContent
from app.services.pdf_generator import _build_pdf_html, _generate_toc_html


class TestTOCGeneration:
    def test_generates_toc(self):
        headings = [
            {"level": 1, "text": "Introduction", "id": "introduction"},
            {"level": 2, "text": "Background", "id": "background"},
            {"level": 2, "text": "Methods", "id": "methods"},
        ]
        toc = _generate_toc_html(headings)
        assert "Introduction" in toc
        assert "Background" in toc
        assert "toc-section" in toc

    def test_empty_headings(self):
        toc = _generate_toc_html([])
        assert toc == ""


class TestPDFHTMLBuild:
    def test_builds_html(self):
        content = ExtractedContent(
            title="Test Document",
            html_content="<p>Hello World</p>",
            text_content="Hello World",
            source_url="https://example.com",
            headings=[],
            extraction_method="test",
        )
        html = _build_pdf_html(content)
        assert "Test Document" in html
        assert "Hello World" in html
        assert "example.com" in html

    def test_includes_author(self):
        content = ExtractedContent(
            title="Doc",
            author="John Doe",
            html_content="<p>Content</p>",
            text_content="Content",
            source_url="https://example.com",
            headings=[],
            extraction_method="test",
        )
        html = _build_pdf_html(content, author="Jane Doe")
        assert "Jane Doe" in html

    def test_custom_settings(self):
        content = ExtractedContent(
            title="Doc",
            html_content="<p>Content</p>",
            text_content="Content",
            source_url="https://example.com",
            headings=[],
            extraction_method="test",
        )
        html = _build_pdf_html(content, page_size="Letter", font_size="large")
        assert "8.5in" in html  # Letter size
        assert "17px" in html   # Large font
