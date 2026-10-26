"""CLI entry point for reflex-code-search."""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import asdict
from pathlib import Path

import typer
from dotenv import load_dotenv

from reflex_search.fallback import JevFallback, default_fallback_scorer
from reflex_search.scorers import AsyncJevScorer, JevScorer, LocalScorer
from reflex_search.searcher import ReflexCodeSearcher

app = typer.Typer(help="Search repository files with a lightweight REFLEX-style loop.")


@app.command()
def search(
    query: str = typer.Argument(..., help="Natural-language question to answer with file discovery."),
    repo_root: str = typer.Argument(".", help="Repository root to search."),
    top_k: int = typer.Option(5, "--top-k", help="Maximum accepted results and candidate leads per list."),
    threshold: float = typer.Option(0.65, "--threshold", help="Accept threshold for the confidence gate."),
    uncertain: float = typer.Option(0.40, "--uncertain", help="Uncertain threshold below which candidates are rejected."),
    min_margin: float = typer.Option(0.0, "--min-margin", help="Minimum score margin for accept (ported from tracecore-reflex)."),
    with_fallback: bool = typer.Option(False, "--with-fallback", help="Enable the default fallback scorer for uncertain candidates."),
    smart_fallback: bool = typer.Option(False, "--smart-fallback", help="Use Jev API as fallback for uncertain candidates (requires OPENROUTER_API_KEY)."),
    live: bool = typer.Option(False, "--live", help="Two-pass: LocalScorer pre-filters, Jev re-scores shortlist (requires OPENROUTER_API_KEY)."),
    live_all: bool = typer.Option(False, "--live-all", help="Score every file with Jev (no pre-filter; requires OPENROUTER_API_KEY)."),
    shortlist: int = typer.Option(20, "--shortlist", help="Number of files to shortlist for two-pass live mode."),
    verbose: bool = typer.Option(False, "--verbose", help="Print the full audit trail after results."),
    stats: bool = typer.Option(False, "--stats", help="Print a one-line session telemetry summary."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of plain text."),
    use_async: bool = typer.Option(False, "--async", help="Use async parallel scoring for --live and --smart-fallback modes."),
) -> None:
    load_dotenv()

    if with_fallback and smart_fallback:
        typer.echo("Error: --with-fallback and --smart-fallback are mutually exclusive.", err=True)
        raise typer.Exit(code=1)
    if live and live_all:
        typer.echo("Error: --live and --live-all select different scoring modes.", err=True)
        raise typer.Exit(code=1)
    if live and (with_fallback or smart_fallback):
        typer.echo("Error: --live cannot be combined with fallback options.", err=True)
        raise typer.Exit(code=1)
    if use_async and not (live or smart_fallback):
        typer.echo("Error: --async requires --live or --smart-fallback.", err=True)
        raise typer.Exit(code=1)
    if live and shortlist < 1:
        typer.echo("Error: --shortlist must be greater than zero.", err=True)
        raise typer.Exit(code=1)
    if top_k < 0:
        typer.echo("Error: --top-k must be non-negative.", err=True)
        raise typer.Exit(code=1)
    if not all(math.isfinite(value) for value in (threshold, uncertain, min_margin)):
        typer.echo("Error: thresholds and --min-margin must be finite numbers.", err=True)
        raise typer.Exit(code=1)
    if not 0.0 <= threshold <= 1.0 or not 0.0 <= uncertain <= 1.0:
        typer.echo("Error: --threshold and --uncertain must be between 0 and 1.", err=True)
        raise typer.Exit(code=1)
    if not 0.0 <= min_margin <= 1.0:
        typer.echo("Error: --min-margin must be between 0 and 1.", err=True)
        raise typer.Exit(code=1)

    root = Path(repo_root).resolve()
    scorer = JevScorer() if live_all else LocalScorer()
    fallback: object = None
    if smart_fallback:
        fallback = JevFallback()
    elif with_fallback:
        fallback = default_fallback_scorer
    searcher = ReflexCodeSearcher(
        repo_root=str(root),
        scorer=scorer,
        accept_threshold=threshold,
        uncertain_threshold=uncertain,
        min_margin=min_margin,
        fallback=fallback,
        top_k=top_k,
    )
    if live and use_async:
        session = asyncio.run(
            searcher.async_search_two_pass(
                query=query,
                async_scorer=AsyncJevScorer(),
                shortlist_size=shortlist,
            )
        )
    elif live:
        session = searcher.search_two_pass(query=query, shortlist_size=shortlist)
    elif smart_fallback and use_async:
        session = asyncio.run(
            searcher.async_search(
                query=query,
                async_scorer=AsyncJevScorer(),
            )
        )
    else:
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
            "candidates": [
                {
                    "path": c.path,
                    "score": c.score,
                    "provider": c.provider,
                    "decision": c.decision,
                    "reason": c.reason,
                    "excerpt": c.excerpt,
                }
                for c in session.candidates
            ],
            "audit_trail": session.audit_trail,
            "telemetry": asdict(session.telemetry) if session.telemetry else None,
        }
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit()

    typer.echo(f"Query: {query}")
    typer.echo(f"Repo: {root}")
    typer.echo("")

    if not session.results:
        typer.echo("No strongly relevant files found.")
        if session.candidates:
            typer.echo("Closest candidates (not accepted by the confidence gate):")
            for candidate in session.candidates:
                typer.echo(
                    f"[{candidate.decision}] [{candidate.provider}] "
                    f"{candidate.score:.2f}  {candidate.path}"
                )
                typer.echo(f"  reason: {candidate.reason}")
                if candidate.excerpt:
                    typer.echo(f"  excerpt: {candidate.excerpt[:180]}")
                typer.echo("")
    else:
        for result in session.results:
            typer.echo(f"[{result.provider}] {result.score:.2f}  {result.path}")
            typer.echo(f"  reason: {result.reason}")
            if result.excerpt:
                typer.echo(f"  excerpt: {result.excerpt[:180]}")
            typer.echo("")

    if verbose and session.audit_trail:
        typer.echo("--- Audit Trail ---")
        for entry in session.audit_trail:
            typer.echo(
                f"  step {entry['step']:>3}  [{entry['provider']}]  "
                f"{entry['score']:.2f}  {entry['decision']:<9}  {entry['path']}"
            )
        typer.echo("")

    if stats and session.telemetry:
        t = session.telemetry
        fb_part = f" | {t.fallback_calls} fallback" if t.fallback_calls else ""
        typer.echo(
            f"{t.files_scanned} files | {t.accepted} accepted | "
            f"{t.uncertain} uncertain{fb_part} | {t.rejected} rejected | "
            f"{t.total_latency_ms:.0f}ms | ${t.total_cost:.4f}"
        )


if __name__ == "__main__":
    app()
