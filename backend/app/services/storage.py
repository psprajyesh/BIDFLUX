"""File validation, filename sanitisation and storage.

This module is the only place that touches the filesystem. Everything it returns is
safe to persist: a sanitised display name and an opaque stored name.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ..config import Settings
from ..enums import DocumentType
from ..errors import ValidationError

#: Extension allow-list. Nothing executable is ever accepted.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".txt", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
)

#: Extensions that are refused with a specific, clearer message.
BLOCKED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".exe", ".bat", ".cmd", ".com", ".scr", ".pif", ".msi", ".dll", ".jar",
        ".js", ".vbs", ".ps1", ".sh", ".php", ".py", ".pyt", ".asp", ".aspx",
        ".cgi", ".pl", ".so", ".elf", ".bin",
    }
)

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_DOT = re.compile(r"\.{2,}")


@dataclass(frozen=True)
class StoredFile:
    """Result of persisting an upload."""

    original_name: str
    stored_name: str
    sanitized_name: str
    extension: str
    size: int
    checksum: str
    content_type: str


def sanitize_filename(raw: str | None) -> str:
    """Reduce an arbitrary client filename to a safe display name.

    Strips directory components, normalises unicode, drops unsafe characters and
    caps the length. Never returns an empty string.
    """
    if not raw:
        return "upload"

    # Defeat both separator styles so "..\\..\\x" cannot survive.
    name = raw.replace("\\", "/").split("/")[-1]
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = _UNSAFE_CHARS.sub("_", name).strip("._-")
    name = _MULTI_DOT.sub(".", name)

    if not name:
        return "upload"

    stem, dot, ext = name.rpartition(".")
    stem = stem[:80] or "upload"
    ext = ext[:12]
    return f"{stem}{dot}{ext}" if dot else stem


def validate_extension(filename: str) -> str:
    """Return the validated lowercase extension, or raise ValidationError."""
    ext = Path(sanitize_filename(filename)).suffix.lower()

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext}' is not permitted.",
            detail={"filename": filename, "blocked": True},
        )
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext or '(none)'}' is not permitted. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
            detail={"filename": filename, "allowed": sorted(ALLOWED_EXTENSIONS)},
        )
    return ext


def validate_size(size: int, settings: Settings) -> None:
    if size <= 0:
        raise ValidationError("Uploaded file is empty.")
    if size > settings.max_upload_bytes:
        raise ValidationError(
            f"File exceeds the {settings.max_upload_mb} MB limit.",
            detail={"size": size, "max_bytes": settings.max_upload_bytes},
        )


def save_upload(
    data: bytes,
    *,
    original_name: str | None,
    content_type: str | None,
    settings: Settings,
    doc_type: DocumentType | None = None,
) -> StoredFile:
    """Validate and persist an upload. Raises ValidationError on any problem."""
    extension = validate_extension(original_name or "")
    validate_size(len(data), settings)

    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    # Opaque stored name: the client never controls the path we write to.
    stored_name = f"{uuid4().hex}{extension}"
    target = settings.storage_dir / stored_name

    try:
        target.write_bytes(data)
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise ValidationError(f"Could not store the file: {exc}") from exc

    return StoredFile(
        original_name=sanitize_filename(original_name),
        stored_name=stored_name,
        sanitized_name=sanitize_filename(original_name),
        extension=extension,
        size=len(data),
        checksum=hashlib.sha256(data).hexdigest(),
        content_type=(content_type or "application/octet-stream")[:128],
    )


def delete_stored_file(stored_name: str, settings: Settings) -> None:
    """Remove a stored file, guarding against traversal."""
    if not stored_name:
        return
    candidate = (settings.storage_dir / Path(stored_name).name).resolve()
    root = settings.storage_dir.resolve()
    if root in candidate.parents and candidate.exists():
        candidate.unlink(missing_ok=True)


def read_text(stored_name: str, settings: Settings) -> str:
    """Best-effort text read for .txt uploads. Returns "" for binary formats.

    The simulated extractor uses this when real text is available and falls back
    to the canonical fixture set otherwise.
    """
    if not stored_name:
        return ""
    path = settings.storage_dir / Path(stored_name).name
    if path.suffix.lower() != ".txt" or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:  # pragma: no cover
        return ""
