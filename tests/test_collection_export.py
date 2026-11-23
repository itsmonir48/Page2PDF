"""
Page2PDF — Collection editing & export tests
Covers page edits with duplicates/rotation, the finalize (export) step and upload guards.
"""
import io

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import routes_collection

client = TestClient(app)


def _pdf_bytes(pages: int, label: str = "Page") -> bytes:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 100), f"{label} {i + 1}", fontsize=20)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def merged_collection():
    col = client.post("/api/collections", json={"title": "Test"}).json()["collection"]
    upload = client.post(
        f"/api/collections/{col['id']}/upload",
        files={"file": ("notes.pdf", _pdf_bytes(3), "application/pdf")},
    ).json()
    assert upload["success"], upload
    merged = client.post(
        f"/api/collections/{col['id']}/merge",
        json={"title": "Test", "author": "Ada", "generate_toc": False},
    ).json()
    assert merged["success"], merged
    return merged["collection"]


def _download(col_id: str, **params) -> fitz.Document:
    res = client.get(f"/api/collections/{col_id}/download", params=params)
    assert res.status_code == 200
    return fitz.open("pdf", res.content)


def test_merge_sets_author(merged_collection):
    doc = _download(merged_collection["id"])
    assert doc.metadata["author"] == "Ada"


def test_edit_pages_supports_duplicates_with_own_rotation(merged_collection):
    res = client.post(
        f"/api/collections/{merged_collection['id']}/edit-pages",
        json={"keep_pages": [0, 0, 2], "rotations_by_position": [0, 90, 0]},
    ).json()
    assert res["success"], res
    assert res["collection"]["edited_total_pages"] == 3
    doc = _download(merged_collection["id"])
    assert [p.rotation for p in doc] == [0, 90, 0]
    assert "Page 1" in doc[1].get_text()
    assert "Page 3" in doc[2].get_text()


def test_rotation_adds_to_existing_rotation(merged_collection):
    col_id = merged_collection["id"]
    client.post(f"/api/collections/{col_id}/edit-pages", json={"keep_pages": [0, 1, 2], "rotations_by_position": [90, 0, 0]})
    client.post(f"/api/collections/{col_id}/edit-pages", json={"keep_pages": [0, 1, 2], "rotations_by_position": [90, 0, 0]})
    assert _download(col_id)[0].rotation == 180


def test_finalize_stamps_numbers_and_watermark(merged_collection):
    col_id = merged_collection["id"]
    res = client.post(
        f"/api/collections/{col_id}/finalize",
        json={"page_numbers": True, "skip_first_page": True, "watermark": "DRAFT"},
    ).json()
    assert res["success"], res
    assert res["collection"]["export_pdf_filename"]
    doc = _download(col_id)
    texts = [p.get_text() for p in doc]
    assert all("DRAFT" in t for t in texts)
    assert "1 / 3" not in texts[0]
    assert "2 / 3" in texts[1]
    # The working copy (used by the editor preview) stays unstamped
    working = _download(col_id, working=1)
    assert "DRAFT" not in working[0].get_text()


def test_finalize_password_encrypts_download(merged_collection):
    col_id = merged_collection["id"]
    res = client.post(f"/api/collections/{col_id}/finalize", json={"password": "s3cret"}).json()
    assert res["collection"]["export_protected"] is True
    doc = _download(col_id)
    assert doc.needs_pass
    assert doc.authenticate("s3cret")


def test_page_edit_clears_previous_export(merged_collection):
    col_id = merged_collection["id"]
    client.post(f"/api/collections/{col_id}/finalize", json={"watermark": "DRAFT"})
    res = client.post(f"/api/collections/{col_id}/edit-pages", json={"keep_pages": [1]}).json()
    assert res["collection"]["export_pdf_filename"] is None
    assert "DRAFT" not in _download(col_id)[0].get_text()


def test_finalize_without_options_clears_export(merged_collection):
    col_id = merged_collection["id"]
    client.post(f"/api/collections/{col_id}/finalize", json={"watermark": "DRAFT"})
    res = client.post(f"/api/collections/{col_id}/finalize", json={}).json()
    assert res["collection"]["export_pdf_filename"] is None


def test_inline_download_disposition(merged_collection):
    res = client.get(f"/api/collections/{merged_collection['id']}/download", params={"inline": 1})
    assert res.headers["content-disposition"].startswith("inline")


def test_thumbnail_zoom_is_clamped(merged_collection):
    res = client.get(f"/api/collections/{merged_collection['id']}/thumbnails/0", params={"zoom": 500})
    assert res.status_code == 200
    img = fitz.Pixmap(res.content)
    assert img.width <= 595 * 3 + 2


def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(routes_collection, "MAX_UPLOAD_SIZE_MB", 0.001)
    col = client.post("/api/collections", json={"title": "T"}).json()["collection"]
    res = client.post(
        f"/api/collections/{col['id']}/upload",
        files={"file": ("big.pdf", _pdf_bytes(40, "Long text " * 20), "application/pdf")},
    ).json()
    assert res["success"] is False
    assert "larger than" in res["error"]


def test_upload_rejects_invalid_pdf():
    col = client.post("/api/collections", json={"title": "T"}).json()["collection"]
    res = client.post(
        f"/api/collections/{col['id']}/upload",
        files={"file": ("fake.pdf", io.BytesIO(b"not a pdf").read(), "application/pdf")},
    ).json()
    assert res["success"] is False


def test_add_url_rejects_private_host():
    col = client.post("/api/collections", json={"title": "T"}).json()["collection"]
    res = client.post(f"/api/collections/{col['id']}/urls", json={"url": "http://127.0.0.1/admin"}).json()
    assert res["success"] is False
    assert not client.get(f"/api/collections/{col['id']}/status").json()["collection"]["items"]
