"""Canonical in-memory representation of an open Markdown file."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Document:
    path: Path | None
    content: str
    utf8_bom: bool = False
