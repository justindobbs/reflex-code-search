"""CLI entry point for reflex-code-search."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from reflex_search.core import ReflexCodeSearcher, SearchSession

app = typer.Typer(help="Search repository files with a lightweight REFLEX-style loop.")


@app.command()
def search(
    query: str = typer.Argument(..., help="Natural-language question to answer with file discovery."),
    repo_root: str = typer.Argument(".", help="Repository root to search."),
    top_k: int = typer.Option(5, "--top-k", help="Maximum number of files to return."),
    threshold: float = typer.Option(0.65, "--threshold", help="Minimum score to accept a candidate."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of plain text."),
) -> None:
    root = Path(repo_root).resolve()
    searcher = ReflexCodeSearcher(repo_root=str(root), threshold=threshold, top_k=top_k)
    session = searcher.search(query=query)
    if json_output:
        payload = {
            "query": session.query,
            "repo_root": session.repo_root,
            "results": [
                {
                    "path": r.path,
                    "score": r.score,
                    "provider": r.provider,
                    "reason": r.reason,
                    "excerpt": r.excerpt,
                }
                for r in session.results
            ],
            "audit_trail": session.audit_trail,
        }
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit()

    typer.echo(f"Query: {query}")
typer.echo(f"Repo: {root}")
    typer.echo("")

    if not session.results:
        typer.echo("No strongly relevant files found.")
        raise typer.Exit()

    for result in session.results:
        typer.echo(f"[{result.provider}] {result.score:.2f}  {result.path}")
        typer.echo(f"  reason: {result.reason}")
        if result.excerpt:
            typer.echo(f"  excerpt: {result.excerpt[:180]}")
        typer.echo("")


if __name__ == "__main__":
    app()
