"""
Page2PDF — Collection API Routes
Handles multi-URL collections, ordering, PDF generation, and merging.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.models.schemas import (
    Collection, CollectionItem, CollectionCreateRequest,
    CollectionAddUrlRequest, CollectionReorderRequest,
    CollectionGenerateRequest, CollectionMergeRequest,
    CollectionResponse, JobStatus, EditPagesRequest
)
from app.services.security import validate_url_security
from app.services.fetcher import fetch_webpage
from app.services.extractor import extract_content
from app.services.pdf_generator import generate_pdf
from app.services.pdf_merger import merge_pdfs
from app.utils.url_utils import normalize_url, is_valid_url_format, sanitize_filename
from app.utils.file_utils import get_output_dir, generate_job_id, file_exists

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory collection store (for simplicity; use DB for production)
collections: Dict[str, Collection] = {}

MAX_URLS_PER_COLLECTION = int(os.getenv("MAX_URLS_PER_COLLECTION", "20"))
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


@router.post("", response_model=CollectionResponse)
async def create_collection(request: CollectionCreateRequest):
    """Create a new PDF collection."""
    col_id = generate_job_id()
    col = Collection(
        id=col_id,
        title=request.title,
        created_at=datetime.now().isoformat(),
        status=JobStatus.QUEUED
    )
    collections[col_id] = col
    return CollectionResponse(success=True, collection=col)


@router.post("/{collection_id}/urls", response_model=CollectionResponse)
async def add_url_to_collection(collection_id: str, request: CollectionAddUrlRequest):
    """Add a URL to a collection."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    
    if len(col.items) >= MAX_URLS_PER_COLLECTION:
        return CollectionResponse(success=False, error=f"Maximum limit of {MAX_URLS_PER_COLLECTION} URLs reached.")

    url = normalize_url(request.url)
    if not is_valid_url_format(url):
        return CollectionResponse(success=False, error="Invalid URL format.")

    # Duplicate check
    for item in col.items:
        if item.url == url:
            return CollectionResponse(success=False, error="This URL has already been added.")

    # Preliminary extraction for title
    title = None
    is_safe, error = validate_url_security(url)
    if is_safe:
        html, _, _ = await fetch_webpage(url)
        if html:
            content = await extract_content(html, url)
            title = content.title

    item_id = generate_job_id()
    new_item = CollectionItem(
        id=item_id,
        url=url,
        title=title or "Untitled Document",
        status=JobStatus.QUEUED
    )
    col.items.append(new_item)
    return CollectionResponse(success=True, collection=col)


@router.delete("/{collection_id}/urls/{url_id}", response_model=CollectionResponse)
async def remove_url_from_collection(collection_id: str, url_id: str):
    """Remove a URL/file from a collection."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    col.items = [item for item in col.items if item.id != url_id]
    return CollectionResponse(success=True, collection=col)


@router.post("/{collection_id}/upload", response_model=CollectionResponse)
async def upload_file_to_collection(
    collection_id: str, 
    file: UploadFile = File(...),
):
    """Upload a local PDF or image directly into the collection."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    
    if len(col.items) >= MAX_URLS_PER_COLLECTION:
        return CollectionResponse(success=False, error=f"Maximum limit of {MAX_URLS_PER_COLLECTION} items reached.")
        
    original_name = file.filename or "uploaded-file"
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        return CollectionResponse(success=False, error="Only PDF, PNG, JPG, JPEG, and WEBP files are supported.")

    import shutil
    
    # Generate unique filename for the uploaded file
    file_id = generate_job_id()
    safe_stem = sanitize_filename(Path(original_name).stem) or "uploaded-file"
    source_filename = f"upload_{file_id}_{safe_stem}{extension}"
    source_path = get_output_dir() / source_filename
    safe_filename = f"upload_{file_id}_{safe_stem}.pdf"
    output_path = get_output_dir() / safe_filename
    
    try:
        with open(source_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if extension != ".pdf":
            from app.services.pdf_merger import convert_image_to_pdf
            if not convert_image_to_pdf(source_path, output_path):
                source_path.unlink(missing_ok=True)
                return CollectionResponse(success=False, error="The uploaded image could not be converted to PDF.")
            source_path.unlink(missing_ok=True)
        else:
            source_path.replace(output_path)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        source_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        return CollectionResponse(success=False, error="Failed to save uploaded file.")
        
    new_item = CollectionItem(
        id=file_id,
        url=f"local://{safe_filename}",
        title=original_name,
        status=JobStatus.COMPLETED,  # Already complete because it's an uploaded PDF
        progress=100,
        filename=safe_filename
    )
    col.items.append(new_item)
    return CollectionResponse(success=True, collection=col)


@router.patch("/{collection_id}/urls/reorder", response_model=CollectionResponse)
async def reorder_urls(collection_id: str, request: CollectionReorderRequest):
    """Reorder URLs in a collection."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    
    new_items = []
    current_items_dict = {item.id: item for item in col.items}
    
    for item_id in request.item_ids:
        if item_id in current_items_dict:
            new_items.append(current_items_dict[item_id])
            
    # Ensure no items were lost
    if len(new_items) != len(col.items):
         return CollectionResponse(success=False, error="Invalid reorder request. Item count mismatch.")
         
    col.items = new_items
    return CollectionResponse(success=True, collection=col)


async def _process_collection_item(item: CollectionItem, request: CollectionGenerateRequest):
    """Process a single URL in a collection."""
    try:
        url = item.url
        item.status = JobStatus.VALIDATING
        item.progress = 5
        item.message = "Validating URL..."
        
        is_safe, security_error = validate_url_security(url)
        if not is_safe:
            item.status = JobStatus.FAILED
            item.error = security_error
            return

        item.status = JobStatus.FETCHING
        item.progress = 15
        item.message = "Fetching webpage..."
        
        html, fetch_error, _ = await fetch_webpage(url)
        if not html:
            item.status = JobStatus.FAILED
            item.error = fetch_error or "Unable to fetch webpage"
            return

        item.status = JobStatus.EXTRACTING
        item.progress = 35
        item.message = "Extracting content..."
        
        content = await extract_content(html, url)
        if not content.html_content or content.quality_score < 10:
            item.status = JobStatus.FAILED
            item.error = "No meaningful article content was found on this page."
            return

        item.title = content.title or item.title

        item.status = JobStatus.CLEANING
        item.progress = 50
        item.message = "Cleaning document..."
        await asyncio.sleep(0.1)

        item.status = JobStatus.FORMATTING
        item.progress = 65
        item.message = "Formatting document..."
        await asyncio.sleep(0.1)

        item.status = JobStatus.GENERATING_PDF
        item.progress = 80
        item.message = "Generating PDF..."

        filename = await generate_pdf(
            content=content,
            title=item.title,
            page_size=request.page_size.value,
            font_size=request.font_size.value,
            include_images=request.include_images,
            include_links=request.include_links,
            include_toc=request.include_toc,
            include_code=request.include_code,
            font_family=request.font_family.value,
        )

        if not filename:
            item.status = JobStatus.FAILED
            item.error = "PDF generation failed."
            return

        item.status = JobStatus.COMPLETED
        item.progress = 100
        item.message = "Ready"
        item.filename = filename

    except Exception as e:
        logger.error(f"Item processing failed: {e}", exc_info=True)
        item.status = JobStatus.FAILED
        item.error = "Unexpected error occurred."


async def _generate_collection_pdfs(col_id: str, request: CollectionGenerateRequest):
    """Background task to generate PDFs for all items in a collection."""
    col = collections.get(col_id)
    if not col:
        return
        
    col.status = JobStatus.GENERATING_PDF
    
    # Process each item
    # We could do this concurrently, but for stability we do it sequentially
    for item in col.items:
        if item.status in [JobStatus.QUEUED, JobStatus.FAILED]:
            await _process_collection_item(item, request)
            
    # Check if overall generation is complete
    any_failed = any(item.status == JobStatus.FAILED for item in col.items)
    all_done = all(item.status in [JobStatus.COMPLETED, JobStatus.FAILED] for item in col.items)
    
    if all_done:
        # We don't mark the whole collection as COMPLETED yet, because MERGING is a separate step
        # But we indicate ready for merge
        col.status = JobStatus.COMPLETED if not any_failed else JobStatus.FAILED
        col.error = "Some sources failed." if any_failed else None


@router.post("/{collection_id}/generate", response_model=CollectionResponse)
async def generate_collection(collection_id: str, request: CollectionGenerateRequest, background_tasks: BackgroundTasks):
    """Start generating individual PDFs for all URLs in the collection."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    
    if not col.items:
         return CollectionResponse(success=False, error="No URLs in collection.")

    # Reset statuses for any that failed or are queued
    for item in col.items:
         if item.status in [JobStatus.QUEUED, JobStatus.FAILED]:
              item.status = JobStatus.QUEUED
              item.progress = 0
              item.error = None
              
    col.status = JobStatus.QUEUED

    background_tasks.add_task(_generate_collection_pdfs, collection_id, request)
    return CollectionResponse(success=True, collection=col)


@router.post("/{collection_id}/retry/{url_id}", response_model=CollectionResponse)
async def retry_url(collection_id: str, url_id: str, request: CollectionGenerateRequest, background_tasks: BackgroundTasks):
    """Retry a specific failed URL."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    item = next((i for i in col.items if i.id == url_id), None)
    
    if not item:
        raise HTTPException(status_code=404, detail="URL not found in collection")

    item.status = JobStatus.QUEUED
    item.progress = 0
    item.error = None
    
    # Run the single item in background
    async def _retry_task():
        col.status = JobStatus.GENERATING_PDF
        await _process_collection_item(item, request)
        all_done = all(i.status in [JobStatus.COMPLETED, JobStatus.FAILED] for i in col.items)
        if all_done:
            any_failed = any(i.status == JobStatus.FAILED for i in col.items)
            col.status = JobStatus.COMPLETED if not any_failed else JobStatus.FAILED
            
    background_tasks.add_task(_retry_task)
    return CollectionResponse(success=True, collection=col)


@router.get("/{collection_id}/status", response_model=CollectionResponse)
async def get_collection_status(collection_id: str):
    """Get current status of a collection."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(success=True, collection=collections[collection_id])


@router.post("/{collection_id}/merge", response_model=CollectionResponse)
async def merge_collection(collection_id: str, request: CollectionMergeRequest):
    """Merge successfully generated PDFs into a single final PDF."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    
    # Prepare list of successfully generated items in their current order
    valid_items = [
        {"filename": item.filename, "title": item.title, "url": item.url}
        for item in col.items if item.status == JobStatus.COMPLETED and item.filename
    ]
    
    if not valid_items:
         return CollectionResponse(success=False, error="No successfully generated PDFs available to merge.")
         
    title = request.title or col.title
    
    filename, total_pages, size_mb = merge_pdfs(
         items=valid_items,
         title=title,
         add_cover_page=request.add_cover_page,
         add_source_separator=request.add_source_separator,
         generate_toc=request.generate_toc
    )
    
    if not filename:
         return CollectionResponse(success=False, error="Failed to merge PDFs.")
         
    col.title = title
    col.final_pdf_filename = filename
    col.final_pdf_size_mb = size_mb
    col.total_pages = total_pages
    col.status = JobStatus.COMPLETED
    
    # Reset any previous edits if we merge again
    col.edited_pdf_filename = None
    col.edited_total_pages = None
    col.edited_size_mb = None
    
    return CollectionResponse(success=True, collection=col)


@router.post("/{collection_id}/edit-pages", response_model=CollectionResponse)
async def apply_page_edits(collection_id: str, request: EditPagesRequest):
    """Edit the final PDF to keep only specific pages (and rotate)."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    current_pdf = col.edited_pdf_filename or col.final_pdf_filename
    if not current_pdf:
         return CollectionResponse(success=False, error="Collection has not been merged yet.")
         
    from app.services.pdf_merger import edit_pdf_pages
    
    filename, total_pages, size_mb = edit_pdf_pages(
        current_pdf,
        request.keep_pages, 
        request.rotations
    )
    
    if not filename:
         return CollectionResponse(success=False, error="Failed to edit PDF pages.")
         
    col.edited_pdf_filename = filename
    col.edited_total_pages = total_pages
    col.edited_size_mb = size_mb
    
    return CollectionResponse(success=True, collection=col)


from fastapi.responses import Response

@router.get("/{collection_id}/thumbnails/{page_index}")
async def get_thumbnail(collection_id: str, page_index: int, zoom: float = 0.5):
    """Get a PNG thumbnail for a specific page of the final PDF."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    current_pdf = col.edited_pdf_filename or col.final_pdf_filename
    if not current_pdf:
         raise HTTPException(status_code=400, detail="Collection has not been merged yet.")
         
    from app.services.pdf_merger import get_pdf_thumbnail
    
    img_bytes = get_pdf_thumbnail(current_pdf, page_index, zoom=zoom)
    
    if not img_bytes:
         raise HTTPException(status_code=404, detail="Thumbnail could not be generated.")
         
    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@router.get("/{collection_id}/download")
async def download_merged_pdf(collection_id: str, custom_filename: Optional[str] = None):
    """Download the final (or edited) merged PDF."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    
    target_filename = col.edited_pdf_filename or col.final_pdf_filename
    
    if not target_filename:
         raise HTTPException(status_code=400, detail="Collection has not been merged yet")
         
    filepath = get_output_dir() / target_filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF file has expired or was deleted")

    if custom_filename and custom_filename.strip():
        safe_name = sanitize_filename(custom_filename.strip()) + ".pdf"
    else:
        safe_name = sanitize_filename(col.title) + ".pdf"
    return FileResponse(
        path=str(filepath),
        filename=safe_name,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/{collection_id}/urls/{url_id}/download")
async def download_individual_pdf(collection_id: str, url_id: str):
    """Download an individual URL's PDF."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    item = next((i for i in col.items if i.id == url_id), None)
    
    if not item or not item.filename:
         raise HTTPException(status_code=400, detail="PDF not ready for this URL")
         
    filepath = get_output_dir() / item.filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF file has expired or was deleted")

    safe_name = sanitize_filename(item.title) + ".pdf"
    return FileResponse(
        path=str(filepath),
        filename=safe_name,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )

@router.post("/{collection_id}/insert-file", response_model=CollectionResponse)
async def insert_file_into_collection_pdf(
    collection_id: str,
    position: str = Form(...),
    page_index: int = Form(0),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
):
    """Insert a PDF, image, or fetched webpage into the active PDF."""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    col = collections[collection_id]
    current_pdf = col.edited_pdf_filename or col.final_pdf_filename
    
    if not current_pdf:
        return CollectionResponse(success=False, error="No active PDF to insert into.")
        
    if bool(file) == bool(url):
        return CollectionResponse(success=False, error="Provide exactly one file or webpage link.")

    insert_path: Path
    temporary_insert_path = False
    if url:
        normalized_url = normalize_url(url)
        is_safe, security_error = validate_url_security(normalized_url)
        if not is_safe:
            return CollectionResponse(success=False, error=security_error)
        html, fetch_error, _ = await fetch_webpage(normalized_url)
        if not html:
            return CollectionResponse(success=False, error=fetch_error or "Unable to fetch webpage.")
        content = await extract_content(html, normalized_url)
        if not content.html_content or content.quality_score < 10:
            return CollectionResponse(success=False, error="No meaningful content was found at this link.")
        generated_filename = await generate_pdf(
            content=content,
            title=content.title or normalized_url,
            include_images=True,
            include_links=True,
            include_toc=True,
            include_code=True,
            page_size="A4",
            font_size="medium",
            font_family="system",
        )
        if not generated_filename:
            return CollectionResponse(success=False, error="Failed to generate PDF from the link.")
        insert_path = get_output_dir() / generated_filename
    else:
        original_name = file.filename or "inserted-file"
        extension = Path(original_name).suffix.lower()
        if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
            return CollectionResponse(success=False, error="Only PDF, PNG, JPG, JPEG, and WEBP files are supported.")

        import shutil
        safe_filename = f"insert_{generate_job_id()}_{sanitize_filename(original_name)}"
        insert_path = get_output_dir() / safe_filename
        temporary_insert_path = True
        try:
            with open(insert_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save inserted file: {e}")
            return CollectionResponse(success=False, error="Failed to save uploaded file.")
        
    from app.services.pdf_merger import insert_file_into_pdf
    
    new_filename, total_pages, size_mb = insert_file_into_pdf(current_pdf, insert_path, position, page_index)
    
    if not new_filename:
        return CollectionResponse(success=False, error="Failed to merge inserted file.")

    if temporary_insert_path:
        insert_path.unlink(missing_ok=True)
        
    col.edited_pdf_filename = new_filename
    col.edited_total_pages = total_pages
    col.edited_size_mb = size_mb
    
    return CollectionResponse(success=True, collection=col)
