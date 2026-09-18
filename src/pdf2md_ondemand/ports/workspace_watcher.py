"""Optional workspace change notification boundary."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class WorkspaceWatcher(Protocol):
    def start(
        self, root: Path, callback: Callable[[tuple[Path, ...]], None]
    ) -> None: ...

    def stop(self) -> None: ...
