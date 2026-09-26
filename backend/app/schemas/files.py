"""
Pydantic schemas for the repository file explorer.

These schemas are intentionally small and read-only — no write operations
on repository files are ever exposed through this API.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class RepositoryFileItem(BaseModel):
    """A single file entry in the repository file tree."""
    path: str
    file_name: str
    language: Optional[str] = None
    extension: str = ""
    file_size: int = 0
    is_directory: bool = False
    category: Optional[str] = None   # reused from analysis if available


class RepositoryFileTree(BaseModel):
    """Response for the file listing/tree endpoint."""
    repository_id: str
    files: list[RepositoryFileItem]
    total_files: int


class FileContentResponse(BaseModel):
    """
    Response for the file content endpoint.

    - content is None when is_binary=True or truncated is set without content.
    - truncated=True means the file was cut at MAX_FILE_SIZE_BYTES and only a
      partial preview is returned.  Currently we refuse oversized files rather
      than truncating, so truncated will always be False when content is present.
    - is_binary=True means the file was detected as binary and no content is
      returned.
    """
    path: str
    file_name: str
    language: Optional[str] = None
    extension: str = ""
    file_size: int = 0
    content: Optional[str] = None
    truncated: bool = False
    is_binary: bool = False
    error: Optional[str] = None      # human-readable, non-sensitive message
