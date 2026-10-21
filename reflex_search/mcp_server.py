"""MCP server exposing reflex-code-search as a tool for AI agents.

Requires the optional ``mcp`` dependency::

    pip install reflex-code-search[mcp]

Run the server::

    python -m reflex_search.mcp_server          # stdio transport (default)
    reflex-search-mcp                           # via entry point
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _exc:
    raise ImportError(
        "The MCP server requires the 'mcp' optional dependency. "
        "Install it with: pip install reflex-code-search[mcp]"
    ) from _exc

from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from reflex_search.fallback import JevFallback
from reflex_search.scorers import JevScorer, LocalScorer
from reflex_search.searcher import ReflexCodeSearcher

load_dotenv()

mcp = FastMCP("reflex-code-search")


@mcp.tool()
def search_codebase(
    query: str,
    repo_root: str = ".",
    top_k: int = 5,
    threshold: float = 0.30,
    live: bool = False,
    smart_fallback: bool = False,
    shortlist: int = 20,
) -> dict:
    """Search a codebase for files relevant to a natural-language question.

    Returns ranked files with scores, excerpts, and telemetry.

    Args:
        query: Natural-language question about the codebase.
        repo_root: Path to the repository root directory.
        top_k: Maximum number of files to return.
        threshold: Accept threshold for the confidence gate (0.0–1.0).
        live: Use two-pass mode (LocalScorer shortlists, Jev re-scores).
        smart_fallback: Use Jev as fallback for uncertain local scores.
        shortlist: Number of files to shortlist in two-pass live mode.
    """
    root = str(Path(repo_root).resolve())

    if live and smart_fallback:
        return {"error": "--live and --smart-fallback are mutually exclusive."}

    scorer = LocalScorer()
    fallback = None
    if smart_fallback:
        fallback = JevFallback()

    searcher = ReflexCodeSearcher(
        repo_root=root,
        scorer=scorer,
        fallback=fallback,
        accept_threshold=threshold,
        uncertain_threshold=0.10 if smart_fallback else 0.40,
        top_k=top_k,
    )

    if live:
        session = searcher.search_two_pass(
            query=query,
            jev_scorer=JevScorer(),
            shortlist_size=shortlist,
        )
    else:
        session = searcher.search(query=query)

    return {
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
        "telemetry": asdict(session.telemetry) if session.telemetry else None,
    }


def main() -> None:
    """Entry point for the MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
