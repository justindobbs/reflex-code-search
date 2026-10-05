"""Tests for repository file discovery and ignore rules."""

from pathlib import Path

from reflex_search.file_collector import collect_files


def _write_file(root: Path, relative_path: str, content: str = "x = 1\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_files_respects_root_gitignore_rules(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\nbuild/\n", encoding="utf-8")
    _write_file(tmp_path, "keep.py")
    _write_file(tmp_path, "ignored.py")
    _write_file(tmp_path, "build/generated.py")

    assert collect_files(str(tmp_path)) == ["keep.py"]


def test_collect_files_respects_nested_gitignore_and_negation(tmp_path: Path) -> None:
    _write_file(tmp_path, "src/nested/.gitignore", "*.py\n!keep.py\n")
    _write_file(tmp_path, "src/visible.py")
    _write_file(tmp_path, "src/nested/hidden.py")
    _write_file(tmp_path, "src/nested/keep.py")

    assert collect_files(str(tmp_path)) == ["src/nested/keep.py", "src/visible.py"]


def test_builtin_excludes_cannot_be_reincluded_by_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("!build/keep.py\n", encoding="utf-8")
    _write_file(tmp_path, "build/keep.py")

    assert collect_files(str(tmp_path)) == []
