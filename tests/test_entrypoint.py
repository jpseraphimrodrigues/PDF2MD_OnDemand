"""The application registers custom schemes before creating QApplication."""

from __future__ import annotations

from pytest import MonkeyPatch

from pdf2md_ondemand import __main__ as entrypoint


def test_startup_registers_asset_scheme_before_qapplication(
    monkeypatch: MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeApplication:
        @staticmethod
        def instance() -> None:
            return None

        def __init__(self, args: list[str]) -> None:
            assert args == []
            events.append("application")

        @staticmethod
        def setOrganizationName(_name: str) -> None:
            events.append("organization")

        @staticmethod
        def setApplicationName(_name: str) -> None:
            events.append("application-name")

        @staticmethod
        def setStyle(_name: str) -> None:
            events.append("style")

        @staticmethod
        def setStyleSheet(styles: str) -> None:
            assert "QMainWindow" in styles
            events.append("theme")

        @staticmethod
        def exec() -> int:
            events.append("exec")
            return 0

    class FakeWindow:
        def __init__(self) -> None:
            events.append("window")

        @staticmethod
        def show() -> None:
            events.append("show")

    monkeypatch.setattr(
        entrypoint, "register_asset_scheme", lambda: events.append("scheme")
    )
    monkeypatch.setattr(entrypoint, "QApplication", FakeApplication)
    monkeypatch.setattr(entrypoint, "MainWindow", FakeWindow)

    assert entrypoint.main() == 0
    assert events == [
        "scheme",
        "application",
        "organization",
        "application-name",
        "style",
        "theme",
        "window",
        "show",
        "exec",
    ]
