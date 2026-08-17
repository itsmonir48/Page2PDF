"""
Page2PDF — PDF Generator
Generates professionally formatted PDFs using WeasyPrint.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

from app.models.schemas import ExtractedContent, PageSize, FontSize
from app.services.code_processor import process_code_blocks
from app.services.image_processor import download_and_embed_images
from app.services.cleaner import clean_html
from app.utils.file_utils import get_output_dir, generate_unique_filename

logger = logging.getLogger(__name__)

# Font size mappings
FONT_SIZES = {
    "small": {"body": "13px", "h1": "26px", "h2": "22px", "h3": "18px", "code": "12px"},
    "medium": {"body": "15px", "h1": "30px", "h2": "24px", "h3": "20px", "code": "13px"},
    "large": {"body": "17px", "h1": "34px", "h2": "28px", "h3": "22px", "code": "14px"},
}

# Page size dimensions
PAGE_SIZES = {
    "A4": {"width": "210mm", "height": "297mm"},
    "Letter": {"width": "8.5in", "height": "11in"},
}


def _generate_toc_html(headings: List[Dict]) -> str:
    """Generate a Table of Contents HTML section."""
    if not headings:
        return ""

    toc_items = []
    for i, h in enumerate(headings):
        level = h.get("level", 2)
        text = h.get("text", "")
        heading_id = h.get("id", f"heading-{i}")
        indent = (level - 1) * 24

        toc_items.append(
            f'<div class="toc-item" style="padding-left: {indent}px;">'
            f'<a href="#{heading_id}" class="toc-link">'
            f'<span class="toc-text">{text}</span>'
            f'<span class="toc-dots"></span>'
            f'</a></div>'
        )

    return f"""
    <div class="toc-section">
        <h2 class="toc-title">Table of Contents</h2>
        <div class="toc-content">
            {''.join(toc_items)}
        </div>
    </div>
    <div class="page-break"></div>
    """


def _add_heading_ids(html_content: str, headings: List[Dict]) -> str:
    """Add IDs to headings for TOC linking."""
    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(html_content, "html.parser")

    heading_idx = 0
    for tag in soup.find_all(re.compile(r'^h[1-6]$')):
        text = tag.get_text(strip=True)
        # Find matching heading
        for h in headings:
            if h.get("text") == text and "used" not in h:
                tag["id"] = h.get("id", f"heading-{heading_idx}")
                h["used"] = True
                break
        heading_idx += 1

    return str(soup)


def _build_pdf_html(
    content: ExtractedContent,
    title: Optional[str] = None,
    author: Optional[str] = None,
    page_size: str = "A4",
    font_size: str = "medium",
    include_images: bool = True,
    include_links: bool = True,
    include_toc: bool = True,
    include_code: bool = True,
    font_family: str = "system",
) -> str:
    """Build the complete HTML document for PDF generation."""

    # Use provided title or extracted title
    doc_title = title or content.title or "Untitled Document"
    doc_author = author or content.author or ""
    doc_date = content.date or ""
    source_url = content.source_url
    generation_date = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # Get font sizes
    fonts = FONT_SIZES.get(font_size, FONT_SIZES["medium"])
    page = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])

    # Clean content
    html_body = clean_html(
        content.html_content,
        include_images=include_images,
        include_links=include_links,
        include_code=include_code,
    )

    # Process code blocks with syntax highlighting
    if include_code:
        html_body = process_code_blocks(html_body)

    # Add heading IDs for TOC
    if include_toc and content.headings:
        html_body = _add_heading_ids(html_body, content.headings)

    # Generate TOC
    toc_html = ""
    if include_toc and content.headings and len(content.headings) >= 2:
        toc_html = _generate_toc_html(content.headings)

    # Build metadata section
    meta_parts = []
    if source_url:
        if include_links:
            meta_parts.append(f'<div class="meta-item"><span class="meta-label">Source:</span> <a href="{source_url}" class="source-link">{source_url}</a></div>')
        else:
            meta_parts.append(f'<div class="meta-item"><span class="meta-label">Source:</span> {source_url}</div>')
    if doc_author:
        meta_parts.append(f'<div class="meta-item"><span class="meta-label">Author:</span> {doc_author}</div>')
    if doc_date:
        meta_parts.append(f'<div class="meta-item"><span class="meta-label">Published:</span> {doc_date}</div>')
    meta_parts.append(f'<div class="meta-item"><span class="meta-label">Generated:</span> {generation_date}</div>')
    meta_html = "\n".join(meta_parts)

    # Load the PDF template
    template_path = Path(__file__).parent.parent / "templates" / "pdf_template.html"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _get_default_template()

    font_stacks = {
        "system": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        "sans-serif": "'Inter', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
        "serif": "Georgia, 'Times New Roman', Times, serif",
        "monospace": "'Fira Code', 'Consolas', 'Courier New', Courier, monospace"
    }
    font_stack = font_stacks.get(font_family, font_stacks["system"])

    # Fill template
    html = template.replace("{{TITLE}}", doc_title)
    html = html.replace("{{META_HTML}}", meta_html)
    html = html.replace("{{TOC_HTML}}", toc_html)
    html = html.replace("{{CONTENT}}", html_body)
    html = html.replace("{{PAGE_WIDTH}}", page["width"])
    html = html.replace("{{PAGE_HEIGHT}}", page["height"])
    html = html.replace("{{FONT_FAMILY_BODY}}", font_stack)
    html = html.replace("{{FONT_SIZE_BODY}}", fonts["body"])
    html = html.replace("{{FONT_SIZE_H1}}", fonts["h1"])
    html = html.replace("{{FONT_SIZE_H2}}", fonts["h2"])
    html = html.replace("{{FONT_SIZE_H3}}", fonts["h3"])
    html = html.replace("{{FONT_SIZE_CODE}}", fonts["code"])
    html = html.replace("{{SOURCE_URL}}", source_url or "")
    html = html.replace("{{GENERATION_DATE}}", generation_date)

    return html


async def generate_pdf(
    content: ExtractedContent,
    title: Optional[str] = None,
    author: Optional[str] = None,
    page_size: str = "A4",
    font_size: str = "medium",
    include_images: bool = True,
    include_links: bool = True,
    include_toc: bool = True,
    include_code: bool = True,
    font_family: str = "system"
) -> Optional[str]:
    """
    Generate a PDF from extracted content.
    Returns the filename of the generated PDF, or None on failure.
    """
    try:
        # Download and embed images
        if include_images:
            logger.info("Downloading and embedding images...")
            content.html_content = await download_and_embed_images(
                content.html_content,
                content.source_url,
            )

        # Build the full HTML document
        logger.info("Building PDF HTML...")
        html = _build_pdf_html(
            content=content,
            title=title,
            author=author,
            page_size=page_size,
            font_size=font_size,
            include_images=include_images,
            include_links=include_links,
            include_toc=include_toc,
            include_code=include_code,
            font_family=font_family,
        )

        # Generate filename
        filename = generate_unique_filename()
        output_path = get_output_dir() / filename

        # Generate PDF with WeasyPrint
        logger.info(f"Generating PDF: {filename}")
        from weasyprint import HTML

        doc_title = title or content.title or "Page2PDF Document"

        html_doc = HTML(string=html)
        pdf = html_doc.write_pdf(
            presentational_hints=True,
        )

        # Write to file
        output_path.write_bytes(pdf)

        file_size_mb = len(pdf) / (1024 * 1024)
        logger.info(f"PDF generated: {filename} ({file_size_mb:.2f} MB)")

        return filename

    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        return None


def _get_default_template() -> str:
    """Return the default PDF template as a fallback."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{TITLE}}</title>
    <style>
        @page {
            size: {{PAGE_WIDTH}} {{PAGE_HEIGHT}};
            margin: 25mm 20mm 25mm 20mm;
            @top-center {
                content: "Page2PDF";
                font-size: 9px;
                color: #94a3b8;
            }
            @bottom-center {
                content: counter(page) " / " counter(pages);
                font-size: 9px;
                color: #94a3b8;
            }
        }
        body {
            font-family: {{FONT_FAMILY_BODY}};
            font-size: {{FONT_SIZE_BODY}};
            line-height: 1.8;
            color: #1e293b;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Helvetica Neue', 'Arial', sans-serif;
            color: #0f172a;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        pre {
            background: #1e1e2e;
            color: #cdd6f4;
            padding: 16px;
            border-radius: 8px;
            font-size: {{FONT_SIZE_CODE}};
            overflow-x: auto;
            white-space: pre;
            border-left: 4px solid #89b4fa;
            page-break-inside: avoid;
        }
        code {
            font-family: 'Consolas', monospace;
        }
        .page-break { page-break-after: always; }
        table { width: 100%; border-collapse: collapse; margin: 1em 0; }
        th, td { padding: 8px 12px; border: 1px solid #cbd5e1; text-align: left; }
        th { background: #f1f5f9; font-weight: bold; }
        img { max-width: 100%; height: auto; }
        a { color: #2563eb; }
    </style>
</head>
<body>
    <h1>{{TITLE}}</h1>
    {{META_HTML}}
    {{TOC_HTML}}
    {{CONTENT}}
</body>
</html>"""
