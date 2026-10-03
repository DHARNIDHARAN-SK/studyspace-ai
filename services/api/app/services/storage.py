import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger

# Canonical bucket identifiers registered in supabase migrations
DOCUMENTS_BUCKET = "documents"
EXPORTS_BUCKET = "exports"

MAX_DOCUMENT_SIZE_BYTES = settings.MAX_UPLOAD_BYTES  # Default 50MB (52,428,800 bytes)
MAX_EXPORT_SIZE_BYTES = 20 * 1024 * 1024             # 20MB (20,971,520 bytes)

ALLOWED_DOCUMENT_EXTENSIONS: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
}

ALLOWED_EXPORT_EXTENSIONS: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class StorageError(AppError):
    """Domain exception for storage path, validation, and I/O failures."""
    def __init__(self, message: str, code: str = "STORAGE_ERROR", status_code: int = 400, action: Optional[str] = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            action=action or "Verify the file format, size, and destination path."
        )


class StorageFileMetadata(BaseModel):
    bucket: str
    storage_path: str
    filename: str
    file_size_bytes: int
    mime_type: str
    checksum_sha256: str
    workspace_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None


def calculate_sha256(data: bytes) -> str:
    """Calculates SHA-256 cryptographic digest of raw byte content."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a client-provided filename to prevent path traversal,
    null bytes, control characters, and OS-reserved names.
    """
    if not filename:
        raise StorageError("Filename cannot be empty.", code="INVALID_FILENAME")

    # Strip directory components and null bytes
    cleaned = os.path.basename(filename.replace("\\", "/")).strip()
    cleaned = cleaned.replace("\x00", "")

    # Replace special characters with underscores, keeping alphanumeric, dots, hyphens, and underscores
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", cleaned)

    # Collapse multiple dots or leading dots that could hide files or cause traversal
    cleaned = re.sub(r"^\.+", "", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)

    if not cleaned or cleaned in (".", ".."):
        raise StorageError("Filename resolves to an invalid or reserved identifier.", code="INVALID_FILENAME")

    return cleaned


def build_document_storage_path(
    workspace_id: uuid.UUID | str,
    project_id: uuid.UUID | str,
    document_id: uuid.UUID | str,
    filename: str,
) -> str:
    """
    Generates the canonical private storage path according to Master Architecture:
    workspaces/{workspace_id}/projects/{project_id}/documents/{document_id}/{filename}
    """
    ws_uuid = uuid.UUID(str(workspace_id))
    proj_uuid = uuid.UUID(str(project_id))
    doc_uuid = uuid.UUID(str(document_id))
    safe_name = sanitize_filename(filename)

    return f"workspaces/{ws_uuid}/projects/{proj_uuid}/documents/{doc_uuid}/{safe_name}"


def build_export_storage_path(
    workspace_id: uuid.UUID | str,
    export_id: uuid.UUID | str,
    filename: str,
) -> str:
    """
    Generates canonical private storage path for generated study guide / conversation exports:
    workspaces/{workspace_id}/exports/{export_id}/{filename}
    """
    ws_uuid = uuid.UUID(str(workspace_id))
    exp_uuid = uuid.UUID(str(export_id))
    safe_name = sanitize_filename(filename)

    return f"workspaces/{ws_uuid}/exports/{exp_uuid}/{safe_name}"


def validate_document_storage_path(
    path: str,
    expected_workspace_id: Optional[uuid.UUID | str] = None,
) -> dict:
    """
    Validates that a storage path conforms strictly to the tenant-isolated format:
    workspaces/{workspace_id}/projects/{project_id}/documents/{document_id}/{filename}
    Prevents path traversal and cross-tenant access.
    """
    # Guard against traversal attempts
    if ".." in path or "\\" in path or path.startswith("/"):
        raise StorageError(
            "Invalid storage path structure: directory traversal detected.",
            code="STORAGE_TRAVERSAL_DETECTED",
            status_code=403,
        )

    parts = path.split("/")
    if len(parts) != 7 or parts[0] != "workspaces" or parts[2] != "projects" or parts[4] != "documents":
        raise StorageError(
            "Storage path does not conform to canonical tenant hierarchy.",
            code="INVALID_STORAGE_PATH",
            status_code=400,
        )

    try:
        ws_id = uuid.UUID(parts[1])
        proj_id = uuid.UUID(parts[3])
        doc_id = uuid.UUID(parts[5])
    except ValueError:
        raise StorageError(
            "Storage path contains invalid UUID identifiers.",
            code="INVALID_PATH_IDENTIFIERS",
            status_code=400,
        )

    if expected_workspace_id is not None:
        if str(ws_id) != str(expected_workspace_id):
            raise StorageError(
                "Access denied: storage path workspace mismatch.",
                code="WORKSPACE_MISMATCH",
                status_code=403,
            )

    filename = parts[6]
    if not filename or filename in (".", ".."):
        raise StorageError("Invalid filename in storage path.", code="INVALID_FILENAME")

    return {
        "workspace_id": ws_id,
        "project_id": proj_id,
        "document_id": doc_id,
        "filename": filename,
    }


def validate_file_spec(
    filename: str,
    file_size_bytes: int,
    content_type: Optional[str] = None,
    is_export: bool = False,
) -> Tuple[str, str]:
    """
    Validates file extension, byte size, and MIME type against architecture boundaries.
    Returns (sanitized_filename, validated_mime_type).
    """
    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()

    allowed_exts = ALLOWED_EXPORT_EXTENSIONS if is_export else ALLOWED_DOCUMENT_EXTENSIONS
    max_size = MAX_EXPORT_SIZE_BYTES if is_export else MAX_DOCUMENT_SIZE_BYTES

    if ext not in allowed_exts:
        supported = ", ".join(allowed_exts.keys())
        raise StorageError(
            f"Unsupported file format '{ext}'. Supported formats: {supported}.",
            code="UNSUPPORTED_FILE_FORMAT",
            status_code=415,
            action=f"Please upload one of the supported academic file types: {supported}",
        )

    if file_size_bytes <= 0:
        raise StorageError("File cannot be empty.", code="EMPTY_FILE", status_code=400)

    if file_size_bytes > max_size:
        max_mb = max_size // (1024 * 1024)
        raise StorageError(
            f"File size exceeds maximum permitted limit of {max_mb} MB.",
            code="FILE_TOO_LARGE",
            status_code=413,
            action=f"Ensure your document is under {max_mb} MB.",
        )

    expected_mime = allowed_exts[ext]
    # If client passed content_type, verify compatibility
    if content_type:
        normalized_client_mime = content_type.split(";")[0].strip().lower()
        # Accept text/plain for markdown
        if ext == ".md" and normalized_client_mime in ("text/plain", "text/markdown", "application/octet-stream"):
            actual_mime = "text/markdown"
        elif ext == ".txt" and normalized_client_mime in ("text/plain", "application/octet-stream"):
            actual_mime = "text/plain"
        elif normalized_client_mime == expected_mime or normalized_client_mime == "application/octet-stream":
            actual_mime = expected_mime
        else:
            actual_mime = expected_mime
    else:
        actual_mime = expected_mime

    return safe_name, actual_mime


class LocalStorageProvider:
    """
    Filesystem storage provider for local development, tests, and offline Docker environments.
    Mirrors Supabase Storage bucket semantics.
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, bucket: str, path: str) -> Path:
        target = (self.base_dir / bucket / path).resolve()
        # Safety check: ensure target stays inside base_dir / bucket
        bucket_dir = (self.base_dir / bucket).resolve()
        if not str(target).startswith(str(bucket_dir)):
            raise StorageError("Path traversal escape prevented.", code="PATH_TRAVERSAL_DETECTED", status_code=403)
        return target

    async def put_object(self, bucket: str, path: str, data: bytes, content_type: str) -> StorageFileMetadata:
        target = self._resolve_path(bucket, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)

        checksum = calculate_sha256(data)
        parts = path.split("/")
        ws_id = uuid.UUID(parts[1]) if len(parts) > 1 and parts[0] == "workspaces" else uuid.uuid4()
        proj_id = uuid.UUID(parts[3]) if len(parts) > 3 and parts[2] == "projects" else None
        doc_id = uuid.UUID(parts[5]) if len(parts) > 5 and parts[4] == "documents" else None

        return StorageFileMetadata(
            bucket=bucket,
            storage_path=path,
            filename=target.name,
            file_size_bytes=len(data),
            mime_type=content_type,
            checksum_sha256=checksum,
            workspace_id=ws_id,
            project_id=proj_id,
            document_id=doc_id,
        )

    async def get_object(self, bucket: str, path: str) -> bytes:
        target = self._resolve_path(bucket, path)
        if not target.exists():
            raise StorageError(f"File not found in storage bucket '{bucket}'.", code="OBJECT_NOT_FOUND", status_code=404)
        with open(target, "rb") as f:
            return f.read()

    async def delete_object(self, bucket: str, path: str) -> bool:
        target = self._resolve_path(bucket, path)
        if target.exists():
            target.unlink()
            return True
        return False

    async def exists(self, bucket: str, path: str) -> bool:
        target = self._resolve_path(bucket, path)
        return target.exists()
