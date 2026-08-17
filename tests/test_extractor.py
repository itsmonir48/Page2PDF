"""
Page2PDF — Extractor Tests
Tests for content extraction.
"""
import pytest
from app.services.extractor import (
    _extract_headings, _extract_code_blocks,
    _extract_images, _score_content,
    extract_with_beautifulsoup,
)
from bs4 import BeautifulSoup


class TestHeadingExtraction:
    def test_extracts_headings(self):
        html = "<h1>Title</h1><h2>Section</h2><h3>Sub</h3>"
        soup = BeautifulSoup(html, "html.parser")
        headings = _extract_headings(soup)
        assert len(headings) == 3
        assert headings[0]["level"] == 1
        assert headings[0]["text"] == "Title"

    def test_empty_html(self):
        soup = BeautifulSoup("", "html.parser")
        headings = _extract_headings(soup)
        assert len(headings) == 0

    def test_no_headings(self):
        soup = BeautifulSoup("<p>Just a paragraph</p>", "html.parser")
        headings = _extract_headings(soup)
        assert len(headings) == 0


class TestCodeBlockExtraction:
    def test_extracts_pre_code(self):
        html = '<pre><code class="language-python">print("hello")</code></pre>'
        soup = BeautifulSoup(html, "html.parser")
        blocks = _extract_code_blocks(soup)
        assert len(blocks) == 1
        assert "print" in blocks[0]["code"]

    def test_pre_without_code(self):
        html = "<pre>some preformatted text</pre>"
        soup = BeautifulSoup(html, "html.parser")
        blocks = _extract_code_blocks(soup)
        assert len(blocks) == 1

    def test_no_code(self):
        soup = BeautifulSoup("<p>No code here</p>", "html.parser")
        blocks = _extract_code_blocks(soup)
        assert len(blocks) == 0


class TestImageExtraction:
    def test_extracts_images(self):
        html = '<img src="https://example.com/photo.jpg" alt="Photo">'
        soup = BeautifulSoup(html, "html.parser")
        images = _extract_images(soup, "https://example.com")
        assert len(images) == 1
        assert images[0]["alt"] == "Photo"

    def test_skips_tracking_pixels(self):
        html = '<img src="https://example.com/tracking-pixel.gif" width="1" height="1">'
        soup = BeautifulSoup(html, "html.parser")
        images = _extract_images(soup, "https://example.com")
        assert len(images) == 0

    def test_skips_social_icons(self):
        html = '<img src="https://example.com/facebook-icon.png">'
        soup = BeautifulSoup(html, "html.parser")
        images = _extract_images(soup, "https://example.com")
        assert len(images) == 0


class TestContentScoring:
    def test_good_content_scores_high(self):
        html = "<h1>Title</h1>" + "<p>" + "word " * 200 + "</p>" * 5
        text = "word " * 1000
        score = _score_content(html, text, "Test Title")
        assert score.overall_score >= 50

    def test_empty_content_scores_zero(self):
        score = _score_content("", "", None)
        assert score.overall_score == 0

    def test_short_content_low_score(self):
        score = _score_content("<p>Short</p>", "Short", None)
        assert score.overall_score < 30


class TestBeautifulSoupExtraction:
    def test_extracts_article(self):
        html = """
        <html><body>
        <nav>Navigation</nav>
        <article>
            <h1>Test Article</h1>
            <p>This is a test article with enough content to pass the minimum threshold.
            It contains multiple sentences and should be extracted properly by the system.
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. More content here.</p>
        </article>
        <footer>Footer</footer>
        </body></html>
        """
        result = extract_with_beautifulsoup(html, "https://example.com")
        assert result is not None
        assert result.title == "Test Article"
        assert "test article" in result.text_content.lower()

    def test_returns_none_for_empty(self):
        result = extract_with_beautifulsoup("<html><body></body></html>", "https://example.com")
        assert result is None
