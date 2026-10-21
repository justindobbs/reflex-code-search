"""AST-based metadata extraction for Python source files.

Replaces regex heuristics (_DEFINITION_RE, _DOCSTRING_RE) with accurate
extraction using the stdlib ``ast`` module.  Falls back to empty results
on syntax errors so callers can revert to regex for broken / partial files.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class PythonMetadata:
    """Structured metadata extracted from a Python source file."""

    definitions: list[str] = field(default_factory=list)
    docstring: str | None = None
    imports: list[str] = field(default_factory=list)


def extract_python_metadata(source: str) -> PythonMetadata:
    """Parse *source* as Python and return definitions, docstring, and imports.

    Returns a :class:`PythonMetadata` with empty/None fields if the source
    cannot be parsed (e.g. syntax errors, non-Python content).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return PythonMetadata()

    definitions: list[str] = []
    imports: list[str] = []

    # Module-level docstring
    docstring = ast.get_docstring(tree)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            definitions.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)

    return PythonMetadata(
        definitions=definitions,
        docstring=docstring,
        imports=imports,
    )
