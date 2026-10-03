from pathlib import Path


def test_searcher_finds_relevant_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src").joinpath("auth.py").write_text(
        "def require_auth(user):\n    if user is None:\n        raise ValueError('unauthorized')\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("This project has auth and login flows.", encoding="utf-8")

    searcher = ReflexCodeSearcher(repo_root=str(repo), threshold=0.5, top_k=5)
    session = searcher.search("Where is authentication checked?")

    assert session.results
    assert any("auth" in result.path.lower() for result in session.results)
    assert session.audit_trail
