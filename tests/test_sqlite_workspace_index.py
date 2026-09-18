from pathlib import Path
from uuid import uuid4

from pdf2md_ondemand.adapters.sqlite_workspace_index import SQLiteWorkspaceIndex


def test_sqlite_rebuild_round_trip_and_disposable_index() -> None:
    root = Path("_test-workspace-") / uuid4().hex
    root.mkdir(parents=True)
    note = root / "note.md"
    source = "# Note\n\n[[Other]] #tag\n"
    note.write_text(source, encoding="utf-8")
    try:
        index = SQLiteWorkspaceIndex(root)
        built = index.rebuild()
        loaded = index.load()
        assert loaded == built
        assert note.read_text(encoding="utf-8") == source
        index.database.unlink()
        assert index.rebuild() == built
        note.write_text("# Edited", encoding="utf-8")
        changed = index.reindex((Path("note.md"),))
        assert changed == index.rebuild()
        note.unlink()
        removed = index.reindex((Path("note.md"),))
        assert removed.notes == ()
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)
