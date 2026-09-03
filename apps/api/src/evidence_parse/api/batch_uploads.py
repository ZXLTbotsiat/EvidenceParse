"""Validate multipart batch uploads and expand safe document archives in memory."""

from __future__ import annotations

import mimetypes
import stat
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from typing import Sequence
from zipfile import BadZipFile, ZipFile, is_zipfile

SUPPORTED_ARCHIVE_DOCUMENTS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class BatchUploadError(ValueError):
    """Base error carrying the HTTP status appropriate for a rejected upload."""

    status_code = 400


class BatchUploadTooLargeError(BatchUploadError):
    status_code = 413


class InvalidArchiveError(BatchUploadError):
    status_code = 422


@dataclass(frozen=True)
class BatchUploadLimits:
    max_files: int
    max_file_bytes: int
    max_batch_bytes: int
    max_archive_entries: int = 100
    max_compression_ratio: int = 200


BufferedUpload = tuple[str, str, bytes]


def is_zip_upload(filename: str) -> bool:
    return PurePosixPath(filename.replace("\\", "/")).suffix.lower() == ".zip"


def expand_batch_uploads(
    uploads: Sequence[BufferedUpload], limits: BatchUploadLimits
) -> list[BufferedUpload]:
    """Return ordinary documents from direct uploads and ZIP members.

    Archives are never extracted to the filesystem. Unsupported archive
    members are ignored, while unsafe or excessive archives reject the whole
    request before a batch record is created.
    """

    documents: list[BufferedUpload] = []
    total_bytes = 0
    for filename, content_type, content in uploads:
        if is_zip_upload(filename):
            expanded = _expand_zip(filename, content, limits)
        else:
            expanded = [(filename, content_type, content)]

        for document in expanded:
            if len(document[2]) > limits.max_file_bytes:
                raise BatchUploadTooLargeError(f"{document[0]} exceeds the per-file size limit.")
            documents.append(document)
            total_bytes += len(document[2])
            if len(documents) > limits.max_files:
                raise BatchUploadTooLargeError(
                    f"A batch can contain at most {limits.max_files} files."
                )
            if total_bytes > limits.max_batch_bytes:
                raise BatchUploadTooLargeError("The batch exceeds the total size limit.")

    if not documents:
        raise BatchUploadError("No supported documents were found in the upload.")
    return documents


def _expand_zip(
    archive_name: str, content: bytes, limits: BatchUploadLimits
) -> list[BufferedUpload]:
    stream = BytesIO(content)
    if not is_zipfile(stream):
        raise InvalidArchiveError(f"{archive_name} is not a valid ZIP archive.")
    stream.seek(0)

    try:
        with ZipFile(stream) as archive:
            members = archive.infolist()
            if len(members) > limits.max_archive_entries:
                raise BatchUploadTooLargeError(
                    f"A ZIP archive can contain at most {limits.max_archive_entries} entries."
                )
            documents = []
            declared_total = 0
            for member in members:
                if member.is_dir():
                    continue
                safe_name = _safe_member_name(member.filename)
                if _is_ignored_metadata(safe_name):
                    continue
                if member.flag_bits & 0x1:
                    raise InvalidArchiveError("Encrypted ZIP entries are not supported.")
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise InvalidArchiveError("Symbolic links are not allowed in ZIP archives.")

                suffix = PurePosixPath(safe_name).suffix.lower()
                content_type = SUPPORTED_ARCHIVE_DOCUMENTS.get(suffix)
                if content_type is None:
                    continue
                if member.file_size > limits.max_file_bytes:
                    raise BatchUploadTooLargeError(f"{safe_name} exceeds the per-file size limit.")
                if _compression_ratio(member.file_size, member.compress_size) > (
                    limits.max_compression_ratio
                ):
                    raise BatchUploadTooLargeError(
                        f"{safe_name} exceeds the allowed ZIP compression ratio."
                    )
                declared_total += member.file_size
                if declared_total > limits.max_batch_bytes:
                    raise BatchUploadTooLargeError(
                        "The ZIP contents exceed the total batch size limit."
                    )
                if len(documents) >= limits.max_files:
                    raise BatchUploadTooLargeError(
                        f"A batch can contain at most {limits.max_files} files."
                    )
                extracted = archive.read(member)
                if len(extracted) != member.file_size:
                    raise InvalidArchiveError(f"{safe_name} could not be read completely.")
                documents.append((safe_name, content_type, extracted))
    except BadZipFile as exc:
        raise InvalidArchiveError(f"{archive_name} is not a valid ZIP archive.") from exc

    if not documents:
        raise BatchUploadError(f"{archive_name} contains no supported documents.")
    return documents


def _safe_member_name(filename: str) -> str:
    if "\\" in filename:
        raise InvalidArchiveError("ZIP entry paths must use forward slashes.")
    path = PurePosixPath(filename)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidArchiveError("ZIP archive contains an unsafe entry path.")
    return path.as_posix()


def _is_ignored_metadata(filename: str) -> bool:
    path = PurePosixPath(filename)
    return "__MACOSX" in path.parts or path.name in {".DS_Store", "Thumbs.db"}


def _compression_ratio(file_size: int, compressed_size: int) -> float:
    if file_size == 0:
        return 1
    return file_size / max(compressed_size, 1)


def normalized_content_type(filename: str, supplied: str) -> str:
    """Prefer a known document MIME type when the client sends a generic one."""

    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    return (
        SUPPORTED_ARCHIVE_DOCUMENTS.get(suffix)
        or supplied
        or (mimetypes.guess_type(filename)[0] or "application/octet-stream")
    )
