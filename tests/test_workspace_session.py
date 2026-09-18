from pdf2md_ondemand.application.document_session import DocumentSession
from pdf2md_ondemand.application.workspace_session import (
    WorkspaceRoot,
    WorkspaceSession,
)
from pdf2md_ondemand.domain.document import Document


def test_workspace_root_has_normalized_absolute_identity() -> None:
    root = WorkspaceRoot("notes/../vault")

    assert root.path.is_absolute()
    assert ".." not in root.path.parts


def test_workspace_session_opens_and_closes_in_memory() -> None:
    session = WorkspaceSession.open("vault")

    assert session.root.path.is_absolute()
    assert session.is_open is True

    session.close()

    assert session.is_open is False


def test_document_session_remains_independent() -> None:
    document_session = DocumentSession.opened(Document(None, ""), None)

    assert document_session.document.path is None
    assert document_session.dirty is False
    assert "workspace" not in DocumentSession.__dataclass_fields__
