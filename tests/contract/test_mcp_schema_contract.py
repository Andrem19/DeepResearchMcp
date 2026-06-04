"""Contract tests: MCP tool schema conformance.

Verifies that the deep_research tool is registered with the correct name
and expected parameters. Tool schema is simplified for local model compatibility.
"""

from __future__ import annotations

import inspect

import pytest


@pytest.mark.contract
class TestMCPToolSchema:
    """Verify MCP tool registration and parameter schema."""

    def _import_deep_research_function(self):
        """Import the deep_research function from mcp_server."""
        from app.mcp_server import deep_research
        return deep_research

    def test_tool_function_name_is_deep_research(self):
        """The MCP tool function is named 'deep_research'."""
        func = self._import_deep_research_function()
        assert func.__name__ == "deep_research"

    def test_tool_has_only_query_parameter(self):
        """The tool signature contains only the query parameter (simplified for local models)."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        assert params == ["query"]

    def test_query_parameter_is_str(self):
        """query is a str parameter (required, no default)."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        assert sig.parameters["query"].default is inspect.Parameter.empty

    def test_return_type_is_str(self):
        """The tool returns a str."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        ann = sig.return_annotation
        assert ann is str or ann == "str"

    def test_tool_is_async(self):
        """The tool function is async."""
        func = self._import_deep_research_function()
        assert inspect.iscoroutinefunction(func)

    def test_tool_has_docstring(self):
        """The tool has a docstring (used by FastMCP for parameter descriptions)."""
        func = self._import_deep_research_function()
        assert func.__doc__ is not None
        assert len(func.__doc__.strip()) > 0

    def test_mcp_server_name_is_deep_research(self):
        """The FastMCP instance is named 'DeepResearch'."""
        from app.mcp_server import mcp
        assert mcp.name == "DeepResearch"
