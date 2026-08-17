"""
Page2PDF — URL Utilities
URL validation, normalization, and helper functions.
"""

import re
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional


def normalize_url(url: str) -> str:
    """Normalize a URL by adding scheme if missing and cleaning up."""
    url = url.strip()

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    # Reconstruct with normalized components
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path or "/",
        parsed.params,
        parsed.query,
        "",  # Remove fragment
    ))

    return normalized


def is_valid_url_format(url: str) -> bool:
    """Check if the URL has a valid format."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme) and bool(parsed.netloc)
    except Exception:
        return False


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or ""
    except Exception:
        return ""


def resolve_relative_url(base_url: str, relative_url: str) -> str:
    """Resolve a relative URL against a base URL."""
    return urljoin(base_url, relative_url)


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Create a safe filename from a title string."""
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title)
    safe = re.sub(r'\s+', '_', safe)
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_. ')

    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')

    return safe or "document"


def get_base_url(url: str) -> str:
    """Get the base URL (scheme + netloc) from a full URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
