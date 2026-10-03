import os
import tempfile
import uuid
from pathlib import Path
import pytest

from app.services.storage import (
    DOCUMENTS_BUCKET,
    EXPORTS_BUCKET,
    LocalStorageProvider,
    StorageError,
    build_document_storage_path,
    build_export_storage_path,
    calculate_sha256,
    sanitize_filename,
    validate_document_storage_path,
    validate_file_spec,
)


def test_sanitize_filename():
    assert sanitize_filename("lecture-1.pdf") == "lecture-1.pdf"
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("my lecture notes (CS101).pdf") == "my_lecture_notes__CS101_.pdf"
    assert sanitize_filename("test\x00file.txt") == "testfile.txt"
    assert sanitize_filename("...hidden.docx") == "hidden.docx"

    with pytest.raises(StorageError):
        sanitize_filename("")

    with pytest.raises(StorageError):
        sanitize_filename("   ")


def test_build_document_storage_path():
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    filename = "Biology_Chapter1.pdf"

    path = build_document_storage_path(ws_id, proj_id, doc_id, filename)
    expected = f"workspaces/{ws_id}/projects/{proj_id}/documents/{doc_id}/Biology_Chapter1.pdf"
    assert path == expected


def test_validate_document_storage_path_valid():
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    filename = "Quantum_Mechanics.pdf"

    path = f"workspaces/{ws_id}/projects/{proj_id}/documents/{doc_id}/{filename}"
    parsed = validate_document_storage_path(path, expected_workspace_id=ws_id)

    assert parsed["workspace_id"] == ws_id
    assert parsed["project_id"] == proj_id
    assert parsed["document_id"] == doc_id
    assert parsed["filename"] == filename


def test_validate_document_storage_path_traversal():
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    # Traversal attempt
    bad_path = f"workspaces/{ws_id}/projects/{proj_id}/documents/{doc_id}/../../secret.txt"
    with pytest.raises(StorageError) as exc_info:
        validate_document_storage_path(bad_path)
    assert exc_info.value.code == "STORAGE_TRAVERSAL_DETECTED"


def test_validate_document_storage_path_workspace_mismatch():
    ws_id_1 = uuid.uuid4()
    ws_id_2 = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    path = f"workspaces/{ws_id_1}/projects/{proj_id}/documents/{doc_id}/test.pdf"
    with pytest.raises(StorageError) as exc_info:
        validate_document_storage_path(path, expected_workspace_id=ws_id_2)
    assert exc_info.value.code == "WORKSPACE_MISMATCH"


def test_validate_file_spec_supported_documents():
    name, mime = validate_file_spec("notes.pdf", 1024)
    assert name == "notes.pdf"
    assert mime == "application/pdf"

    name, mime = validate_file_spec("report.docx", 2048)
    assert name == "report.docx"
    assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    name, mime = validate_file_spec("slides.pptx", 4096)
    assert name == "slides.pptx"
    assert mime == "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    name, mime = validate_file_spec("readme.txt", 512)
    assert name == "readme.txt"
    assert mime == "text/plain"

    name, mime = validate_file_spec("summary.md", 256)
    assert name == "summary.md"
    assert mime == "text/markdown"


def test_validate_file_spec_unsupported_extensions():
    for bad_file in ["malware.exe", "script.sh", "archive.zip", "data.csv", "image.png"]:
        with pytest.raises(StorageError) as exc_info:
            validate_file_spec(bad_file, 1024)
        assert exc_info.value.code == "UNSUPPORTED_FILE_FORMAT"


def test_validate_file_spec_size_limits():
    # Zero bytes
    with pytest.raises(StorageError) as exc_info:
        validate_file_spec("empty.pdf", 0)
    assert exc_info.value.code == "EMPTY_FILE"

    # Exceeding 50MB
    oversized = 52_428_801
    with pytest.raises(StorageError) as exc_info:
        validate_file_spec("huge.pdf", oversized)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_calculate_sha256():
    data = b"StudySpace AI secure document content"
    checksum = calculate_sha256(data)
    assert len(checksum) == 64
    assert checksum == "efe4d1e28d783b1966a3ca2688221c0ea628dd7e27b4de1bf6bc94fe026b49b4"


@pytest.mark.asyncio
async def test_local_storage_provider_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        provider = LocalStorageProvider(Path(tmp_dir))

        ws_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        rel_path = build_document_storage_path(ws_id, proj_id, doc_id, "lecture1.pdf")
        content = b"%PDF-1.4 Mock PDF stream for StudySpace AI testing"

        # 1. Put object
        meta = await provider.put_object(DOCUMENTS_BUCKET, rel_path, content, "application/pdf")
        assert meta.bucket == DOCUMENTS_BUCKET
        assert meta.file_size_bytes == len(content)
        assert meta.checksum_sha256 == calculate_sha256(content)

        # 2. Exists
        assert await provider.exists(DOCUMENTS_BUCKET, rel_path) is True

        # 3. Get object
        fetched = await provider.get_object(DOCUMENTS_BUCKET, rel_path)
        assert fetched == content

        # 4. Delete object
        deleted = await provider.delete_object(DOCUMENTS_BUCKET, rel_path)
        assert deleted is True
        assert await provider.exists(DOCUMENTS_BUCKET, rel_path) is False
