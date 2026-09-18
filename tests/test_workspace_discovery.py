from pathlib import Path
from uuid import uuid4

import pytest

from pdf2md_ondemand.application.workspace_session import (
    WorkspaceDiscoveryError,
    discover_markdown,
)


def test_discovery_sorts_filters_and_preserves_unicode_paths() -> None:
    root = Path("_test-workspace-") / uuid4().hex
    (root / "z.md").parent.mkdir(parents=True)
    try:
        (root / "z.md").write_text("z", encoding="utf-8")
        (root / "Árvore").mkdir()
        (root / "Árvore" / "nota.MD").write_text("n", encoding="utf-8")
        (root / ".pdf2md").mkdir()
        (root / ".pdf2md" / "hidden.md").write_text("x", encoding="utf-8")
        (root / "private").mkdir()
        (root / "private" / "hidden.md").write_text("x", encoding="utf-8")
        tree = discover_markdown(root, ignored_directories=("private",))
        assert [entry.name for entry in tree] == ["Árvore", "z.md"]
        assert tree[0].children[0].relative_path == Path("Árvore") / "nota.MD"
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


def test_discovery_ignores_symlinks() -> None:
    root = Path("_test-workspace-") / uuid4().hex
    outside = root.parent / f"{root.name}-outside"
    root.mkdir(parents=True)
    outside.mkdir(parents=True)
    try:
        (outside / "secret.md").write_text("secret", encoding="utf-8")
        try:
            (root / "escape").symlink_to(outside, target_is_directory=True)
            (root / "shortcut.md").symlink_to(outside / "secret.md")
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                pytest.skip("symlink creation requires unavailable Windows privilege")
            raise
        assert discover_markdown(root) == ()
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


def test_discovery_rejects_missing_or_file_root() -> None:
    root = Path("_test-workspace-") / uuid4().hex
    root.mkdir(parents=True)
    file_root = root / "note.md"
    file_root.write_text("note", encoding="utf-8")
    try:
        with pytest.raises(WorkspaceDiscoveryError):
            discover_markdown(root / "missing")
        with pytest.raises(WorkspaceDiscoveryError):
            discover_markdown(file_root)
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)
