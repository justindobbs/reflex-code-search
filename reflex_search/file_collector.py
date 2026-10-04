"""File discovery for repository scanning."""

from __future__ import annotations

from pathlib import Path

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
    """Walk *repo_root* and return sorted relative paths of scannable text files."""
    root = Path(repo_root)
    files: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        if any(part.endswith(sfx) for part in path.parts for sfx in _EXCLUDE_SUFFIXES):
            continue
        if path.suffix.lower() not in DEFAULT_TEXT_SUFFIXES:
            continue
        try:
            if path.stat().st_size > 250_000:
                continue
        except OSError:
            continue
        files.append(str(path.relative_to(root)))

    files.sort()
    return files


def read_file(relative_path: str, repo_root: str) -> str:
    """Read a file relative to *repo_root*."""
    root = Path(repo_root)
    return (root / relative_path).read_text(encoding="utf-8", errors="ignore")
