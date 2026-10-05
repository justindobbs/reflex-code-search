"""File discovery for repository scanning."""

from __future__ import annotations

import os
from pathlib import Path

from pathspec import GitIgnoreSpec

DEFAULT_TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
}

DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".idea",
    ".vscode",
    ".DS_Store",
    ".env",
}

_EXCLUDE_SUFFIXES = {".egg-info"}


def collect_files(repo_root: str) -> list[str]:
    """Return sorted scannable paths, respecting nested ``.gitignore`` files."""
    root = Path(repo_root).resolve()
    files: list[str] = []
    specs_by_dir: dict[str, list[tuple[str, GitIgnoreSpec]]] = {".": []}

    def is_ignored(
        path: str,
        *,
        is_dir: bool,
        specs: list[tuple[str, GitIgnoreSpec]],
    ) -> bool:
        ignored = False
        match_path = f"{path}/" if is_dir else path
        for base, spec in specs:
            relative = match_path if base == "." else match_path.removeprefix(f"{base}/")
            if relative == match_path and base != ".":
                continue
            result = spec.check_file(relative)
            if result.index is not None:
                ignored = bool(result.include)
        return ignored

    for current, dirnames, filenames in os.walk(root, topdown=True):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root).as_posix() or "."
        inherited_specs = specs_by_dir.pop(relative_dir, [])

        ignore_file = current_path / ".gitignore"
        try:
            patterns = ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            patterns = []
        if patterns:
            inherited_specs = [
                *inherited_specs,
                (relative_dir, GitIgnoreSpec.from_lines(patterns)),
            ]

        kept_dirs: list[str] = []
        for dirname in dirnames:
            child = current_path / dirname
            relative = child.relative_to(root).as_posix()
            if any(part in DEFAULT_EXCLUDES for part in Path(relative).parts):
                continue
            if any(
                part.endswith(sfx)
                for part in Path(relative).parts
                for sfx in _EXCLUDE_SUFFIXES
            ):
                continue
            if is_ignored(relative, is_dir=True, specs=inherited_specs):
                continue
            kept_dirs.append(dirname)
            specs_by_dir[relative] = inherited_specs
        dirnames[:] = kept_dirs

        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            relative_parts = Path(relative).parts
            if any(part in DEFAULT_EXCLUDES for part in relative_parts):
                continue
            if any(
                part.endswith(sfx)
                for part in relative_parts
                for sfx in _EXCLUDE_SUFFIXES
            ):
                continue
            if is_ignored(relative, is_dir=False, specs=inherited_specs):
                continue
            if path.suffix.lower() not in DEFAULT_TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 250_000:
                    continue
            except OSError:
                continue
            files.append(relative)

    files.sort()
    return files


def read_file(relative_path: str, repo_root: str) -> str:
    """Read a file relative to *repo_root*."""
    root = Path(repo_root)
    return (root / relative_path).read_text(encoding="utf-8", errors="ignore")
