"""Setuptools build hook for compiling and packaging the local frontend."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from setuptools import build_meta
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


class BuildPy(_build_py):
    """Add compiled frontend files to the temporary Python build tree."""

    def run(self) -> None:
        super().run()
        package_frontend = (
            Path(self.build_lib)
            / "pdf2md_ondemand"
            / "ui"
            / "desktop"
            / "frontend"
        )
        package_frontend.mkdir(parents=True, exist_ok=True)
        for source in (FRONTEND / "src").glob("*.html"):
            shutil.copy2(source, package_frontend / source.name)
        for name in ("editor.js", "preview.js"):
            shutil.copy2(FRONTEND / "dist" / name, package_frontend / name)


def _build_frontend() -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError(
            "Building PDF2MD requires Node.js/npm to compile the frontend. "
            "Install Node.js, then retry the package build."
        )
    if not (FRONTEND / "node_modules").is_dir():
        subprocess.run([npm, "ci"], cwd=FRONTEND, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)


def build_wheel(
    wheel_directory: str,
    config_settings: object = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a wheel with the compiled frontend package data."""
    _build_frontend()
    return build_meta.build_wheel(
        wheel_directory, config_settings, metadata_directory
    )


def build_editable(
    wheel_directory: str,
    config_settings: object = None,
    metadata_directory: str | None = None,
) -> str:
    """Build an editable install after compiling frontend package data."""
    _build_frontend()
    return build_meta.build_editable(
        wheel_directory, config_settings, metadata_directory
    )


def build_sdist(sdist_directory: str, config_settings: object = None) -> str:
    """Build an sdist that includes the frontend source tree."""
    return build_meta.build_sdist(sdist_directory, config_settings)


def get_requires_for_build_wheel(config_settings: object = None) -> list[str]:
    return build_meta.get_requires_for_build_wheel(config_settings)


def get_requires_for_build_editable(config_settings: object = None) -> list[str]:
    return build_meta.get_requires_for_build_editable(config_settings)


def get_requires_for_build_sdist(config_settings: object = None) -> list[str]:
    return build_meta.get_requires_for_build_sdist(config_settings)


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: object = None
) -> str:
    return build_meta.prepare_metadata_for_build_wheel(
        metadata_directory, config_settings
    )


def prepare_metadata_for_build_editable(
    metadata_directory: str, config_settings: object = None
) -> str:
    return build_meta.prepare_metadata_for_build_editable(
        metadata_directory, config_settings
    )
