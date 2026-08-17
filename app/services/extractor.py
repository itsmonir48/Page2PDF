"""
Page2PDF — Content Extractor
Smart extraction using multiple strategies with quality scoring.
"""

import re
import logging
from typing import Optional, List, Dict
from bs4 import BeautifulSoup, Tag

from app.models.schemas import ExtractedContent, ContentQualityScore

logger = logging.getLogger(__name__)


def _score_content(html: str, text: str, title: Optional[str]) -> ContentQualityScore:
    """Score the quality of extracted content."""
    soup = BeautifulSoup(html, "html.parser") if html else None

    text_length = len(text) if text else 0
    paragraphs = text.count("\n\n") + 1 if text else 0
    heading_count = len(soup.find_all(re.compile(r'^h[1-6]$'))) if soup else 0
    code_blocks = len(soup.find_all(['pre', 'code'])) if soup else 0
    images = len(soup.find_all('img')) if soup else 0
    tables = len(soup.find_all('table')) if soup else 0
    html_length = len(html) if html else 1
    ratio = text_length / html_length if html_length > 0 else 0

    # Calculate overall score (0-100)
    score = 0
    if text_length > 200:
        score += 20
    if text_length > 500:
        score += 10
    if text_length > 1000:
        score += 10
    if paragraphs > 2:
        score += 15
    if heading_count > 0:
        score += 15
    if title:
        score += 10
    if ratio > 0.1:
        score += 10
    if code_blocks > 0:
        score += 5
    if images > 0:
        score += 5

    return ContentQualityScore(
        text_length=text_length,
        paragraph_count=paragraphs,
        heading_count=heading_count,
        has_title=bool(title),
        code_block_count=code_blocks,
        image_count=images,
        table_count=tables,
        text_to_html_ratio=round(ratio, 4),
        overall_score=min(score, 100),
    )


def extract_with_trafilatura(html: str, url: str) -> Optional[ExtractedContent]:
    """Extract content using Trafilatura."""
    try:
        import trafilatura
        from trafilatura.settings import use_config

        config = use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")

        # Extract main content as HTML
        extracted_html = trafilatura.extract(
            html,
            output_format="html",
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_links=True,
            include_formatting=True,
            favor_recall=True,
            config=config,
            url=url,
        )

        # Extract as text for scoring
        extracted_text = trafilatura.extract(
            html,
            output_format="txt",
            include_comments=False,
            include_tables=True,
            config=config,
            url=url,
        )

        if not extracted_html or not extracted_text:
            return None

        # Extract metadata
        metadata = trafilatura.extract_metadata(html, default_url=url)
        title = metadata.title if metadata else None
        author = metadata.author if metadata else None
        date = str(metadata.date) if metadata and metadata.date else None

        # Parse for headings, code blocks, images
        soup = BeautifulSoup(extracted_html, "html.parser")
        headings = _extract_headings(soup)
        code_blocks = _extract_code_blocks(soup)
        images = _extract_images(soup, url)

        quality = _score_content(extracted_html, extracted_text, title)

        return ExtractedContent(
            title=title,
            author=author,
            date=date,
            html_content=extracted_html,
            text_content=extracted_text,
            source_url=url,
            images=images,
            code_blocks=code_blocks,
            headings=headings,
            extraction_method="trafilatura",
            quality_score=quality.overall_score,
        )

    except Exception as e:
        logger.error(f"Trafilatura extraction error: {e}")
        return None


def extract_with_beautifulsoup(html: str, url: str) -> Optional[ExtractedContent]:
    """
    Extract content using BeautifulSoup with heuristic-based main content detection.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Try to find <h1> as a more specific title
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True)
            if h1_text:
                title = h1_text

        # Remove unwanted elements
        for selector in [
            "nav", "header", "footer", "aside",
            ".nav", ".navbar", ".header", ".footer", ".sidebar",
            ".advertisement", ".ad", ".ads", ".adsbygoogle",
            ".social", ".share", ".comments", ".comment",
            ".cookie", ".popup", ".modal", ".overlay",
            ".newsletter", ".signup", ".subscribe",
            ".related", ".recommended", ".trending",
            "#nav", "#header", "#footer", "#sidebar",
            "#comments", "#cookie-banner",
            "script", "style", "noscript", "iframe",
            "[role='navigation']", "[role='banner']",
            "[role='contentinfo']", "[role='complementary']",
        ]:
            for element in soup.select(selector):
                element.decompose()

        # Try to find main content area
        main_content = None
        content_selectors = [
            "article",
            "main",
            "[role='main']",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".content",
            ".article-body",
            ".post-body",
            "#content",
            "#main-content",
            "#article",
            ".markdown-body",
            ".documentation",
            ".doc-content",
            ".tutorial-content",
        ]

        for selector in content_selectors:
            found = soup.select_one(selector)
            if found and len(found.get_text(strip=True)) > 200:
                main_content = found
                break

        if not main_content:
            # Fallback: find the largest text block
            body = soup.find("body")
            if body:
                main_content = body
            else:
                main_content = soup

        # Extract content
        content_html = str(main_content)
        content_text = main_content.get_text(separator="\n", strip=True)

        if len(content_text) < 100:
            return None

        # Extract metadata
        author = None
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta:
            author = author_meta.get("content")

        date = None
        date_meta = soup.find("meta", attrs={"property": "article:published_time"})
        if date_meta:
            date = date_meta.get("content")
        if not date:
            date_meta = soup.find("time")
            if date_meta:
                date = date_meta.get("datetime") or date_meta.get_text(strip=True)

        headings = _extract_headings(main_content)
        code_blocks = _extract_code_blocks(main_content)
        images = _extract_images(main_content, url)

        quality = _score_content(content_html, content_text, title)

        return ExtractedContent(
            title=title,
            author=author,
            date=date,
            html_content=content_html,
            text_content=content_text,
            source_url=url,
            images=images,
            code_blocks=code_blocks,
            headings=headings,
            extraction_method="beautifulsoup",
            quality_score=quality.overall_score,
        )

    except Exception as e:
        logger.error(f"BeautifulSoup extraction error: {e}")
        return None


def extract_with_readability(html: str, url: str) -> Optional[ExtractedContent]:
    """Extract content using readability-lxml."""
    try:
        from readability import Document

        doc = Document(html, url=url)
        content_html = doc.summary()
        title = doc.title()

        if not content_html or len(content_html) < 100:
            return None

        soup = BeautifulSoup(content_html, "html.parser")
        content_text = soup.get_text(separator="\n", strip=True)

        if len(content_text) < 50:
            return None

        headings = _extract_headings(soup)
        code_blocks = _extract_code_blocks(soup)
        images = _extract_images(soup, url)

        quality = _score_content(content_html, content_text, title)

        return ExtractedContent(
            title=title,
            html_content=content_html,
            text_content=content_text,
            source_url=url,
            images=images,
            code_blocks=code_blocks,
            headings=headings,
            extraction_method="readability",
            quality_score=quality.overall_score,
        )

    except Exception as e:
        logger.error(f"Readability extraction error: {e}")
        return None


def _extract_headings(soup) -> List[Dict]:
    """Extract headings from parsed HTML."""
    headings = []
    for tag in soup.find_all(re.compile(r'^h[1-6]$')):
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        if text:
            heading_id = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
            headings.append({
                "level": level,
                "text": text,
                "id": heading_id,
            })
    return headings


def _extract_code_blocks(soup) -> List[Dict]:
    """Extract code blocks from parsed HTML."""
    code_blocks = []

    for pre in soup.find_all("pre"):
        code_tag = pre.find("code")
        if code_tag:
            code_text = code_tag.get_text()
            # Detect language from class
            lang = _detect_language_from_classes(code_tag.get("class", []))
            code_blocks.append({
                "code": code_text,
                "language": lang,
            })
        else:
            code_text = pre.get_text()
            if code_text.strip():
                code_blocks.append({
                    "code": code_text,
                    "language": None,
                })

    return code_blocks


def _detect_language_from_classes(classes: list) -> Optional[str]:
    """Detect programming language from CSS classes."""
    if not classes:
        return None

    language_patterns = {
        "python": ["python", "py", "language-python", "lang-python", "lang-py"],
        "javascript": ["javascript", "js", "language-javascript", "lang-javascript", "lang-js"],
        "typescript": ["typescript", "ts", "language-typescript", "lang-typescript"],
        "java": ["java", "language-java", "lang-java"],
        "c": ["language-c", "lang-c"],
        "cpp": ["cpp", "c++", "language-cpp", "lang-cpp", "language-c++"],
        "csharp": ["csharp", "c#", "language-csharp", "lang-csharp", "language-cs"],
        "html": ["html", "language-html", "lang-html"],
        "css": ["css", "language-css", "lang-css"],
        "sql": ["sql", "language-sql", "lang-sql"],
        "bash": ["bash", "shell", "sh", "language-bash", "lang-bash", "language-shell"],
        "json": ["json", "language-json", "lang-json"],
        "xml": ["xml", "language-xml", "lang-xml"],
        "markdown": ["markdown", "md", "language-markdown", "lang-markdown"],
        "go": ["go", "golang", "language-go", "lang-go"],
        "rust": ["rust", "language-rust", "lang-rust"],
        "ruby": ["ruby", "rb", "language-ruby", "lang-ruby"],
        "php": ["php", "language-php", "lang-php"],
    }

    for cls in classes:
        cls_lower = cls.lower()
        for lang, patterns in language_patterns.items():
            if cls_lower in patterns or any(p in cls_lower for p in patterns):
                return lang

    return None


def _extract_images(soup, base_url: str) -> List[Dict]:
    """Extract relevant images from parsed HTML."""
    from urllib.parse import urljoin

    images = []
    seen_urls = set()

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not src:
            continue

        # Resolve relative URLs
        if not src.startswith(("http://", "https://", "data:")):
            src = urljoin(base_url, src)

        # Skip duplicates
        if src in seen_urls:
            continue
        seen_urls.add(src)

        # Skip irrelevant images
        alt = img.get("alt", "")
        src_lower = src.lower()

        # Skip tracking pixels, icons, logos, social media images
        skip_patterns = [
            "tracking", "pixel", "1x1", "spacer", "beacon",
            "logo", "favicon", "icon", "badge",
            "facebook", "twitter", "linkedin", "instagram",
            "share", "social", "button", "arrow",
            "advertisement", "ad-", "advert",
        ]

        if any(p in src_lower for p in skip_patterns):
            continue

        # Skip very small images (likely icons/tracking)
        width = img.get("width")
        height = img.get("height")
        if width and height:
            try:
                w = int(str(width).replace("px", ""))
                h = int(str(height).replace("px", ""))
                if w < 50 or h < 50:
                    continue
            except ValueError:
                pass

        caption = img.get("title") or alt
        images.append({
            "src": src,
            "alt": alt,
            "caption": caption,
        })

    return images


async def extract_content(html: str, url: str) -> ExtractedContent:
    """
    Main extraction function. Uses multiple strategies and picks the best result.
    """
    results = []

    # Strategy 1: Trafilatura (best for articles)
    logger.info("Trying Trafilatura extraction...")
    trafilatura_result = extract_with_trafilatura(html, url)
    if trafilatura_result:
        results.append(trafilatura_result)
        logger.info(f"Trafilatura score: {trafilatura_result.quality_score}")

    # Strategy 2: Readability (good for articles with complex layouts)
    logger.info("Trying Readability extraction...")
    readability_result = extract_with_readability(html, url)
    if readability_result:
        results.append(readability_result)
        logger.info(f"Readability score: {readability_result.quality_score}")

    # Strategy 3: BeautifulSoup (custom heuristic, fallback)
    logger.info("Trying BeautifulSoup extraction...")
    bs_result = extract_with_beautifulsoup(html, url)
    if bs_result:
        results.append(bs_result)
        logger.info(f"BeautifulSoup score: {bs_result.quality_score}")

    if not results:
        # Return an empty result
        return ExtractedContent(
            source_url=url,
            extraction_method="none",
            quality_score=0,
        )

    # Pick the result with the highest quality score
    best = max(results, key=lambda r: r.quality_score)
    logger.info(f"Selected extraction method: {best.extraction_method} (score: {best.quality_score})")

    # If the best score is low with Trafilatura, but BS found more code blocks,
    # prefer BS result for programming pages
    if best.extraction_method == "trafilatura" and bs_result:
        if len(bs_result.code_blocks) > len(best.code_blocks) + 2:
            logger.info("Switching to BeautifulSoup for better code block preservation")
            # Merge: use BS content but Trafilatura metadata
            best.html_content = bs_result.html_content
            best.text_content = bs_result.text_content
            best.code_blocks = bs_result.code_blocks
            best.images = bs_result.images
            best.extraction_method = f"{best.extraction_method}+beautifulsoup"

    return best
