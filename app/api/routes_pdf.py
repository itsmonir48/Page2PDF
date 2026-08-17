"""
Page2PDF — PDF Generation API Routes
Handles PDF generation, job status, and downloads.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.schemas import (
    GeneratePDFRequest, GeneratePDFResponse,
    JobStatusResponse, JobStatus, ExtractedContent,
)
from app.services.security import validate_url_security
from app.services.fetcher import fetch_webpage
from app.services.extractor import extract_content
from app.services.pdf_generator import generate_pdf
from app.utils.url_utils import normalize_url, is_valid_url_format, sanitize_filename
from app.utils.file_utils import get_output_dir, file_exists, generate_job_id

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job store (for simplicity; use DB for production)
jobs: Dict[str, dict] = {}


def _update_job(job_id: str, **kwargs):
    """Update job status."""
    if job_id in jobs:
        jobs[job_id].update(kwargs)
        logger.info(f"Job {job_id}: {kwargs.get('status', '')} - {kwargs.get('message', '')}")


async def _process_pdf_job(job_id: str, request: GeneratePDFRequest):
    """Background task to process a PDF generation job."""
    try:
        url = normalize_url(request.url)

        # Step 1: Validate
        _update_job(job_id, status=JobStatus.VALIDATING, progress=5, message="Validating URL...")

        is_safe, security_error = validate_url_security(url)
        if not is_safe:
            _update_job(job_id, status=JobStatus.FAILED, error=security_error, message="URL validation failed")
            return

        # Step 2: Fetch
        _update_job(job_id, status=JobStatus.FETCHING, progress=15, message="Fetching webpage...")

        html, fetch_error, fetch_method = await fetch_webpage(url)
        if not html:
            _update_job(job_id, status=JobStatus.FAILED, error=fetch_error or "Unable to fetch webpage",
                        message="Fetching failed")
            return

        # Step 3: Extract
        _update_job(job_id, status=JobStatus.EXTRACTING, progress=35, message="Extracting content...")

        content = await extract_content(html, url)
        if not content.html_content or content.quality_score < 10:
            _update_job(job_id, status=JobStatus.FAILED,
                        error="No meaningful article content was found on this page.",
                        message="Extraction failed")
            return

        # Update title if found
        doc_title = request.title or content.title or "Untitled Document"
        _update_job(job_id, title=doc_title)

        # Step 4: Clean
        _update_job(job_id, status=JobStatus.CLEANING, progress=50, message="Cleaning document...")
        await asyncio.sleep(0.1)  # Allow status update to propagate

        # Step 5: Format
        _update_job(job_id, status=JobStatus.FORMATTING, progress=65, message="Formatting document...")
        await asyncio.sleep(0.1)

        # Step 6: Generate PDF
        _update_job(job_id, status=JobStatus.GENERATING_PDF, progress=80, message="Generating PDF...")

        filename = await generate_pdf(
            content=content,
            title=request.title,
            author=request.author,
            page_size=request.page_size.value if request.page_size else "A4",
            font_size=request.font_size.value if request.font_size else "medium",
            include_images=request.include_images,
            include_links=request.include_links,
            include_toc=request.include_toc,
            include_code=request.include_code,
        )

        if not filename:
            _update_job(job_id, status=JobStatus.FAILED,
                        error="PDF generation failed. Please try again.",
                        message="PDF generation failed")
            return

        # Step 7: Complete
        _update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="PDF ready for download!",
            filename=filename,
            download_url=f"/api/download/{job_id}",
            title=doc_title,
        )

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        _update_job(job_id, status=JobStatus.FAILED,
                    error="An unexpected error occurred. Please try again.",
                    message="Processing failed")


@router.post("/generate-pdf", response_model=GeneratePDFResponse)
async def start_pdf_generation(request: GeneratePDFRequest, background_tasks: BackgroundTasks):
    """
    Start a PDF generation job. Returns a job ID for status polling.
    """
    url = normalize_url(request.url)

    # Quick validation
    if not is_valid_url_format(url):
        return GeneratePDFResponse(
            success=False,
            error="Invalid URL format. Please enter a valid webpage URL.",
        )

    # Create job
    job_id = generate_job_id()
    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "progress": 0,
        "message": "Job queued...",
        "title": request.title,
        "filename": None,
        "download_url": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }

    # Start background processing
    background_tasks.add_task(_process_pdf_job, job_id, request)

    return GeneratePDFResponse(
        success=True,
        job_id=job_id,
        message="PDF generation started. Use the job ID to check status.",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a PDF generation job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatusResponse(**job)


@router.get("/download/{job_id}")
async def download_pdf(job_id: str):
    """Download the generated PDF for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="PDF is not ready yet")

    filename = job.get("filename")
    if not filename:
        raise HTTPException(status_code=404, detail="PDF file not found")

    filepath = get_output_dir() / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF file has expired or was deleted")

    # Create a safe download filename
    title = job.get("title", "document")
    safe_name = sanitize_filename(title) + ".pdf"

    return FileResponse(
        path=str(filepath),
        filename=safe_name,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
        },
    )
