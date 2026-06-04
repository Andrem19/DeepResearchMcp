"""Contract tests: MCP tool schema conformance.

Verifies that the deep_research tool is registered with the correct name
and expected parameters.
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

    def test_tool_has_expected_parameters(self):
        """The tool signature contains exactly the expected parameters."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        expected = ["query", "depth", "max_sources", "recency_days", "output_format"]
        assert params == expected

    def test_query_parameter_is_str(self):
        """query is a str parameter (required, no default)."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        assert sig.parameters["query"].default is inspect.Parameter.empty

    def test_depth_default_is_standard(self):
        """depth defaults to 'standard'."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        assert sig.parameters["depth"].default == "standard"

    def test_max_sources_default_is_8(self):
        """max_sources defaults to 8."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        assert sig.parameters["max_sources"].default == 8

    def test_recency_days_default_is_none(self):
        """recency_days defaults to None."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        assert sig.parameters["recency_days"].default is None

    def test_output_format_default_is_markdown(self):
        """output_format defaults to 'markdown'."""
        func = self._import_deep_research_function()
        sig = inspect.signature(func)
        assert sig.parameters["output_format"].default == "markdown"

    def test_return_type_is_str(self):
        """The tool returns a str (annotation may be string form due to `from __future__ import annotations`)."""
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
        # FastMCP stores the name attribute
        assert mcp.name == "DeepResearch"
