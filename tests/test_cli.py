"""Integration tests for the CLI."""

import json

from typer.testing import CliRunner

from reflex_search.cli import app

runner = CliRunner()


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "auth.py").write_text(
        "def require_auth(user):\n    if user is None:\n        raise ValueError('unauthorized')\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("This project has auth and login flows.", encoding="utf-8")
    return repo


class TestCliPlainText:
    def test_basic_search(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["Where is auth checked?", str(repo), "--threshold", "0.3"])
        assert result.exit_code == 0
        assert "Query:" in result.output

    def test_no_results(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()
        result = runner.invoke(app, ["anything", str(repo)])
        assert result.exit_code == 0
        assert "No strongly relevant files found." in result.output


class TestCliJson:
    def test_json_output(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["Where is auth?", str(repo), "--json", "--threshold", "0.3"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "query" in payload
        assert "results" in payload
        assert "audit_trail" in payload


class TestCliFallback:
    def test_with_fallback_flag(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["auth", str(repo), "--with-fallback", "--threshold", "0.3"])
        assert result.exit_code == 0


class TestCliVerbose:
    def test_verbose_shows_audit(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["auth", str(repo), "--verbose", "--threshold", "0.3"])
        assert result.exit_code == 0
        assert "Audit Trail" in result.output
