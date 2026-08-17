"""
Page2PDF — Content Cleaner
Cleans and normalizes extracted HTML content for PDF generation.
"""

import re
import logging
from bs4 import BeautifulSoup, NavigableString, Comment

logger = logging.getLogger(__name__)

# Elements to always remove
REMOVE_TAGS = {
    "script", "style", "noscript", "iframe", "embed", "object",
    "video", "audio", "canvas", "svg", "form", "input",
    "button", "select", "textarea",
}

# Classes/IDs indicating unwanted content
UNWANTED_PATTERNS = [
    "advertisement", "ad-", "ads-", "adsbygoogle", "sponsor",
    "social", "share", "sharing", "tweet", "facebook", "twitter",
    "instagram", "linkedin", "pinterest",
    "comment", "comments", "disqus",
    "cookie", "consent", "gdpr", "privacy",
    "popup", "modal", "overlay", "lightbox",
    "newsletter", "subscribe", "signup", "sign-up",
    "related", "recommended", "trending", "popular",
    "sidebar", "widget", "aside",
    "footer", "nav", "navbar", "navigation", "menu", "breadcrumb",
    "header-top", "top-bar", "toolbar",
    "author-bio", "about-author",
    "rating", "vote", "like",
    "banner", "promo", "promotion",
    "print-", "no-print",
    "hidden", "d-none", "sr-only",
]


def clean_html(html_content: str, include_images: bool = True, include_links: bool = True,
               include_code: bool = True) -> str:
    """
    Clean and normalize HTML content for PDF generation.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove unwanted tags
    for tag_name in REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove elements with unwanted classes/IDs
    _remove_unwanted_elements(soup)

    # Handle images
    if not include_images:
        for img in soup.find_all("img"):
            img.decompose()

    # Handle links
    if not include_links:
        for a in soup.find_all("a"):
            a.unwrap()  # Keep text, remove link

    # Handle code blocks
    if not include_code:
        for pre in soup.find_all("pre"):
            pre.decompose()
        for code in soup.find_all("code"):
            code.unwrap()

    # Clean up empty elements
    _remove_empty_elements(soup)

    # Normalize whitespace in text nodes
    _normalize_whitespace(soup)

    # Remove excessive line breaks
    html_str = str(soup)
    html_str = re.sub(r'(<br\s*/?>\s*){3,}', '<br><br>', html_str)
    html_str = re.sub(r'(\s*\n\s*){3,}', '\n\n', html_str)

    return html_str


def _remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """Remove elements that match unwanted patterns in their class or ID."""
    for element in soup.find_all(True):
        if _is_unwanted_element(element):
            element.decompose()


def _is_unwanted_element(element) -> bool:
    """Check if an element should be removed based on its attributes."""
    # Check class names
    classes = element.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes).lower()
    else:
        class_str = str(classes).lower()

    # Check ID
    element_id = (element.get("id") or "").lower()

    # Check role
    role = (element.get("role") or "").lower()

    combined = f"{class_str} {element_id} {role}"

    for pattern in UNWANTED_PATTERNS:
        if pattern in combined:
            return True

    # Check aria-hidden
    if element.get("aria-hidden") == "true":
        return True

    # Check display:none in inline styles
    style = (element.get("style") or "").lower()
    if "display:none" in style.replace(" ", "") or "display: none" in style:
        return True

    return False


def _remove_empty_elements(soup: BeautifulSoup) -> None:
    """Remove elements that are empty or contain only whitespace."""
    # Keep these even if empty (structural/semantic elements)
    keep_empty = {"br", "hr", "img", "td", "th", "tr", "thead", "tbody"}

    changed = True
    max_iterations = 3

    while changed and max_iterations > 0:
        changed = False
        max_iterations -= 1
        for element in soup.find_all(True):
            if element.name in keep_empty:
                continue
            if not element.get_text(strip=True) and not element.find(["img", "table", "pre", "code"]):
                element.decompose()
                changed = True


def _normalize_whitespace(soup: BeautifulSoup) -> None:
    """Normalize whitespace in text nodes (but preserve code blocks)."""
    for text_node in soup.find_all(string=True):
        parent = text_node.parent
        if parent and parent.name in ("pre", "code"):
            continue  # Preserve whitespace in code
        if isinstance(text_node, NavigableString):
            cleaned = re.sub(r'[ \t]+', ' ', str(text_node))
            text_node.replace_with(NavigableString(cleaned))
