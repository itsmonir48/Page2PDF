"""
Page2PDF — Models and Schemas
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from enum import Enum
from datetime import datetime


class PageSize(str, Enum):
    A4 = "A4"
    LETTER = "Letter"


class FontSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class FontFamily(str, Enum):
    SYSTEM = "system"
    SANS_SERIF = "sans-serif"
    SERIF = "serif"
    MONOSPACE = "monospace"


class JobStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    FETCHING = "fetching"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    FORMATTING = "formatting"
    GENERATING_PDF = "generating_pdf"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request Models ──────────────────────────────────────────────

class ExtractRequest(BaseModel):
    url: str = Field(..., description="The URL of the webpage to extract content from")


class GeneratePDFRequest(BaseModel):
    url: str = Field(..., description="The URL of the webpage")
    title: Optional[str] = Field(None, description="Custom document title (auto-extracted if not provided)")
    author: Optional[str] = Field(None, description="Document author")
    page_size: PageSize = Field(PageSize.A4, description="Page size for the PDF")
    font_size: FontSize = Field(FontSize.MEDIUM, description="Font size for the PDF")
    include_images: bool = Field(True, description="Whether to include images")
    include_links: bool = Field(True, description="Whether to include hyperlinks")
    include_toc: bool = Field(True, description="Whether to include table of contents")
    include_code: bool = Field(True, description="Whether to include code blocks")


# ── Response Models ─────────────────────────────────────────────

class ExtractResponse(BaseModel):
    success: bool
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    content_preview: Optional[str] = None
    word_count: Optional[int] = None
    has_code_blocks: bool = False
    has_images: bool = False
    has_tables: bool = False
    heading_count: int = 0
    extraction_method: Optional[str] = None
    error: Optional[str] = None


class GeneratePDFResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(0, ge=0, le=100)
    message: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


# ── Internal Models ─────────────────────────────────────────────

class ExtractedContent(BaseModel):
    """Internal model for extracted webpage content."""
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    html_content: str = ""
    text_content: str = ""
    source_url: str = ""
    images: List[dict] = Field(default_factory=list)
    code_blocks: List[dict] = Field(default_factory=list)
    headings: List[dict] = Field(default_factory=list)
    extraction_method: str = "unknown"
    quality_score: float = 0.0


class ContentQualityScore(BaseModel):
    """Scoring for content extraction quality."""
    text_length: int = 0
    paragraph_count: int = 0
    heading_count: int = 0
    has_title: bool = False
    code_block_count: int = 0
    image_count: int = 0
    table_count: int = 0
    text_to_html_ratio: float = 0.0
    overall_score: float = 0.0


# ── Collection Models ───────────────────────────────────────────

class CollectionItem(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    message: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    page_count: int = 0


class Collection(BaseModel):
    id: str
    title: str
    items: List[CollectionItem] = Field(default_factory=list)
    status: JobStatus = JobStatus.QUEUED
    created_at: str
    final_pdf_filename: Optional[str] = None
    final_pdf_size_mb: float = 0.0
    total_pages: int = 0
    
    # Page management fields
    edited_pdf_filename: Optional[str] = None
    edited_total_pages: Optional[int] = None
    edited_size_mb: Optional[float] = None
    
    error: Optional[str] = None


class CollectionCreateRequest(BaseModel):
    title: str = "Study Material Collection"


class CollectionAddUrlRequest(BaseModel):
    url: str


class CollectionReorderRequest(BaseModel):
    item_ids: List[str]


class CollectionGenerateRequest(BaseModel):
    page_size: PageSize = Field(PageSize.A4)
    font_size: FontSize = Field(FontSize.MEDIUM)
    font_family: FontFamily = Field(FontFamily.SYSTEM)
    include_images: bool = Field(True)
    include_links: bool = Field(True)
    include_toc: bool = Field(True)
    include_code: bool = Field(True)


class CollectionMergeRequest(BaseModel):
    title: Optional[str] = None
    add_cover_page: bool = Field(False)
    add_source_separator: bool = Field(False)
    generate_toc: bool = Field(True)


class EditPagesRequest(BaseModel):
    keep_pages: List[int] = Field(..., description="0-indexed list of pages to keep in the final PDF, in desired order")
    rotations: Optional[Dict[int, int]] = Field(None, description="Map of page index to rotation degrees (90, 180, 270)")


class CollectionResponse(BaseModel):
    success: bool
    collection: Optional[Collection] = None
    error: Optional[str] = None
