"""
Page2PDF — Main Application
FastAPI application setup with routes, static files, and middleware.
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

# Load environment
load_dotenv()

from app.api.routes_extract import router as extract_router
from app.api.routes_pdf import router as pdf_router
from app.api.routes_collection import router as collection_router
from app.utils.file_utils import get_output_dir, cleanup_old_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Page2PDF starting up...")
    get_output_dir()  # Ensure output directory exists
    cleanup_old_files(max_age_hours=float(os.getenv("PDF_RETENTION_HOURS", "1")))
    logger.info("Page2PDF ready!")
    yield
    # Shutdown
    logger.info("Page2PDF shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Page2PDF",
    description="Turn Any Webpage Into a Clean, Professional PDF",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API routers
app.include_router(extract_router, prefix="/api", tags=["extraction"])
app.include_router(pdf_router, prefix="/api", tags=["pdf"])
app.include_router(collection_router, prefix="/api/collections", tags=["collections"])


@app.get("/", response_class=HTMLResponse)
async def serve_homepage():
    """Serve the main homepage."""
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Page2PDF</h1><p>Template not found.</p>", status_code=500)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Page2PDF"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Endpoint not found"},
        )
    return HTMLResponse(
        content="<h1>404 - Page Not Found</h1>",
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 handler."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error. Please try again."},
    )
