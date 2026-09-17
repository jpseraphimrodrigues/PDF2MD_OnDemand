"""Filesystem validation for read-only raster assets in the Preview."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote

_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MALFORMED_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")


class AssetPathError(ValueError):
    """An asset URL is invalid or outside its authorized document directory."""


def resolve_asset_path(root: Path, encoded_path: str) -> Path:
    """Decode and canonically validate a relative raster path under ``root``."""
    if not encoded_path or _MALFORMED_ESCAPE.search(encoded_path):
        raise AssetPathError("empty or malformed asset path")
    try:
        relative = unquote(encoded_path, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AssetPathError("asset path is not valid UTF-8") from exc
    if "\x00" in relative or "\\" in relative:
        raise AssetPathError("invalid path separator")

    posix = PurePosixPath(relative)
    windows = PureWindowsPath(relative)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise AssetPathError("absolute paths are not allowed")
    parts = relative.split("/")
    if any(part in {"..", ""} for part in parts):
        raise AssetPathError("path traversal is not allowed")
    if not relative or relative == ".":
        raise AssetPathError("directory listing is not allowed")
    if Path(parts[-1]).suffix.lower() not in _ALLOWED_SUFFIXES:
        raise AssetPathError("asset type is not allowed")

    try:
        canonical_root = root.resolve(strict=True)
        target = canonical_root.joinpath(*parts).resolve(strict=True)
        target.relative_to(canonical_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise AssetPathError("asset does not resolve inside its document root") from exc
    if not target.is_file():
        raise AssetPathError("asset is not a regular file")
    return target
