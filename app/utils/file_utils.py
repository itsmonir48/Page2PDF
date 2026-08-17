"""
Page2PDF — File Utilities
File management, cleanup, and path helpers.
"""

import os
import uuid
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default output directory
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


def get_output_dir() -> Path:
    """Get the output directory path, creating it if necessary."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def generate_unique_filename(prefix: str = "page2pdf", extension: str = "pdf") -> str:
    """Generate a unique filename with UUID."""
    unique_id = uuid.uuid4().hex[:12]
    timestamp = int(time.time())
    return f"{prefix}_{timestamp}_{unique_id}.{extension}"


def generate_job_id() -> str:
    """Generate a unique job ID."""
    return uuid.uuid4().hex


def get_file_path(filename: str) -> Path:
    """Get the full path for a file in the output directory."""
    return get_output_dir() / filename


def file_exists(filename: str) -> bool:
    """Check if a file exists in the output directory."""
    return get_file_path(filename).exists()


def delete_file(filename: str) -> bool:
    """Delete a file from the output directory."""
    try:
        filepath = get_file_path(filename)
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        return False


def cleanup_old_files(max_age_hours: float = 1.0) -> int:
    """
    Delete files older than max_age_hours from the output directory.
    Returns the number of files deleted.
    """
    output_dir = get_output_dir()
    max_age_seconds = max_age_hours * 3600
    now = time.time()
    deleted_count = 0

    try:
        for filepath in output_dir.iterdir():
            if filepath.is_file():
                file_age = now - filepath.stat().st_mtime
                if file_age > max_age_seconds:
                    filepath.unlink()
                    deleted_count += 1
                    logger.info(f"Cleaned up old file: {filepath.name}")
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old files")

    return deleted_count


def get_file_size_mb(filepath: Path) -> float:
    """Get file size in megabytes."""
    return filepath.stat().st_size / (1024 * 1024)
