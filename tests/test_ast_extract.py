"""Tests for the AST-based Python metadata extractor."""

from reflex_search.ast_extract import PythonMetadata, extract_python_metadata


class TestExtractPythonMetadata:
    def test_empty_source(self):
        meta = extract_python_metadata("")
        assert meta.definitions == []
        assert meta.docstring is None
        assert meta.imports == []

    def test_syntax_error_returns_empty(self):
        meta = extract_python_metadata("def broken(:\n    pass")
        assert meta == PythonMetadata()

    def test_non_python_content_returns_empty(self):
        meta = extract_python_metadata("this is not valid python {{{")
        assert meta == PythonMetadata()

    def test_module_docstring(self):
        source = '"""Module-level docstring."""\n\nx = 1\n'
        meta = extract_python_metadata(source)
        assert meta.docstring == "Module-level docstring."

    def test_no_module_docstring(self):
        source = "x = 1\n"
        meta = extract_python_metadata(source)
        assert meta.docstring is None

    def test_function_definitions(self):
        source = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        meta = extract_python_metadata(source)
        assert "foo" in meta.definitions
        assert "bar" in meta.definitions

    def test_async_function_definitions(self):
        source = "async def fetch():\n    pass\n"
        meta = extract_python_metadata(source)
        assert "fetch" in meta.definitions

    def test_class_definitions(self):
        source = "class MyClass:\n    pass\n\nclass AnotherClass:\n    pass\n"
        meta = extract_python_metadata(source)
        assert "MyClass" in meta.definitions
        assert "AnotherClass" in meta.definitions

    def test_nested_definitions(self):
        source = (
            "class Outer:\n"
            "    def method(self):\n"
            "        pass\n"
            "    class Inner:\n"
            "        pass\n"
        )
        meta = extract_python_metadata(source)
        assert "Outer" in meta.definitions
        assert "method" in meta.definitions
        assert "Inner" in meta.definitions

    def test_imports(self):
        source = "import os\nimport sys\n"
        meta = extract_python_metadata(source)
        assert "os" in meta.imports
        assert "sys" in meta.imports

    def test_from_imports(self):
        source = "from pathlib import Path\nfrom os.path import join, exists\n"
        meta = extract_python_metadata(source)
        assert "pathlib.Path" in meta.imports
        assert "os.path.join" in meta.imports
        assert "os.path.exists" in meta.imports

    def test_combined_metadata(self):
        source = (
            '"""A sample module."""\n'
            "import json\n"
            "from pathlib import Path\n\n"
            "class Config:\n"
            '    """Config class."""\n'
            "    pass\n\n"
            "def load():\n"
            "    pass\n"
        )
        meta = extract_python_metadata(source)
        assert meta.docstring == "A sample module."
        assert "Config" in meta.definitions
        assert "load" in meta.definitions
        assert "json" in meta.imports
        assert "pathlib.Path" in meta.imports

    def test_real_world_scorer_content(self):
        source = (
            '"""Relevance scorers for reflex-code-search."""\n\n'
            "import re\n\n"
            "class LocalScorer:\n"
            '    """Fast local scorer."""\n'
            "    def score(self, file_path, query, content):\n"
            "        pass\n\n"
            "class JevScorer:\n"
            '    """Jev API scorer."""\n'
            "    def score(self, file_path, query, content):\n"
            "        pass\n"
        )
        meta = extract_python_metadata(source)
        assert meta.docstring == "Relevance scorers for reflex-code-search."
        assert "LocalScorer" in meta.definitions
        assert "JevScorer" in meta.definitions
        assert "score" in meta.definitions
        assert "re" in meta.imports
