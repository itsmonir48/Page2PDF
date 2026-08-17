"""
Page2PDF — Extract API Routes
Handles content extraction from URLs.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.security import validate_url_security
from app.services.fetcher import fetch_webpage
from app.services.extractor import extract_content
from app.utils.url_utils import normalize_url, is_valid_url_format

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract_url_content(request: ExtractRequest):
    """
    Extract and preview content from a webpage URL.
    Returns metadata and content preview without generating a PDF.
    """
    url = normalize_url(request.url)

    # Validate URL format
    if not is_valid_url_format(url):
        return ExtractResponse(success=False, error="Invalid URL format. Please enter a valid webpage URL.")

    # Security validation
    is_safe, security_error = validate_url_security(url)
    if not is_safe:
        return ExtractResponse(success=False, error=security_error)

    # Fetch the webpage
    html, fetch_error, fetch_method = await fetch_webpage(url)
    if not html:
        return ExtractResponse(success=False, error=fetch_error or "Unable to fetch the webpage.")

    # Extract content
    try:
        content = await extract_content(html, url)
    except Exception as e:
        logger.error(f"Extraction error for {url}: {e}", exc_info=True)
        return ExtractResponse(success=False, error="Content extraction failed. Please try a different URL.")

    if not content.html_content or content.quality_score < 10:
        return ExtractResponse(
            success=False,
            error="No meaningful article content was found on this page."
        )

    # Build preview
    preview = content.text_content[:500] + "..." if len(content.text_content) > 500 else content.text_content
    word_count = len(content.text_content.split()) if content.text_content else 0

    return ExtractResponse(
        success=True,
        title=content.title,
        author=content.author,
        date=content.date,
        content_preview=preview,
        word_count=word_count,
        has_code_blocks=len(content.code_blocks) > 0,
        has_images=len(content.images) > 0,
        has_tables=bool(content.html_content and "<table" in content.html_content.lower()),
        heading_count=len(content.headings),
        extraction_method=content.extraction_method,
    )
