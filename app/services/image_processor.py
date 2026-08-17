"""
Page2PDF — Image Processor
Downloads, validates, and processes images for PDF embedding.
"""

import os
import re
import io
import base64
import logging
import httpx
from typing import Optional, List, Dict, Tuple
from urllib.parse import urljoin, urlparse
from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
MAX_IMAGES_PER_PAGE = int(os.getenv("MAX_IMAGES_PER_PAGE", "50"))
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
REQUEST_TIMEOUT = 15  # Shorter timeout for images

# Maximum dimensions for embedded images
MAX_IMAGE_WIDTH = 700
MAX_IMAGE_HEIGHT = 800


async def download_and_embed_images(html_content: str, base_url: str) -> str:
    """
    Download images referenced in HTML and embed them as base64 data URIs.
    This ensures images are included in the PDF.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    images = soup.find_all("img")
    processed_count = 0

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(REQUEST_TIMEOUT),
        follow_redirects=True,
        max_redirects=3,
    ) as client:
        for img in images:
            if processed_count >= MAX_IMAGES_PER_PAGE:
                logger.warning("Maximum image count reached, skipping remaining images")
                break

            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue

            # Skip already-embedded images
            if src.startswith("data:"):
                processed_count += 1
                continue

            # Resolve relative URLs
            if not src.startswith(("http://", "https://")):
                src = urljoin(base_url, src)

            # Download and embed
            data_uri = await _download_image(client, src)
            if data_uri:
                img["src"] = data_uri
                # Add responsive styling
                img["style"] = (
                    "max-width: 100%; height: auto; display: block; "
                    "margin: 12px auto; border-radius: 4px;"
                )
                processed_count += 1
            else:
                # Remove failed images but preserve alt text
                alt = img.get("alt", "")
                if alt:
                    img.replace_with(f"[Image: {alt}]")
                else:
                    img.decompose()

    logger.info(f"Processed {processed_count} images")
    return str(soup)


async def _download_image(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """
    Download an image and return it as a base64 data URI.
    """
    try:
        response = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        })

        if response.status_code != 200:
            logger.debug(f"Failed to download image (HTTP {response.status_code}): {url}")
            return None

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return None

        content = response.content
        if len(content) > MAX_IMAGE_SIZE_BYTES:
            logger.debug(f"Image too large ({len(content)} bytes): {url}")
            return None

        # Process and resize the image
        processed = _process_image(content, content_type)
        if processed:
            img_bytes, mime_type = processed
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            return f"data:{mime_type};base64,{b64}"

        return None

    except httpx.TimeoutException:
        logger.debug(f"Timeout downloading image: {url}")
        return None
    except Exception as e:
        logger.debug(f"Error downloading image {url}: {e}")
        return None


def _process_image(image_data: bytes, content_type: str) -> Optional[Tuple[bytes, str]]:
    """
    Process an image: validate, resize if necessary, and convert.
    Returns (processed_bytes, mime_type) or None.
    """
    try:
        img = Image.open(io.BytesIO(image_data))

        # Skip tiny images (likely icons/tracking pixels)
        if img.width < 30 or img.height < 30:
            return None

        # Resize if too large
        if img.width > MAX_IMAGE_WIDTH or img.height > MAX_IMAGE_HEIGHT:
            img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)

        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ("RGBA", "LA", "P"):
            # Keep as PNG to preserve transparency
            output = io.BytesIO()
            img.save(output, format="PNG", optimize=True)
            output.seek(0)
            return output.read(), "image/png"
        else:
            # Convert to JPEG for smaller size
            if img.mode != "RGB":
                img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            output.seek(0)
            return output.read(), "image/jpeg"

    except Exception as e:
        logger.debug(f"Error processing image: {e}")
        return None
