"""
Tools registry — exposes AVAILABLE_TOOLS and get_tools_schema() for the agent loop.
"""

from .base import Tool, ToolResult
from .filesystem import ReadFileTool, WriteFileTool, EditFileTool, DeleteFileTool
from .navigation import ListDirTool, GlobFilesTool, SearchCodeTool
from .web import WebSearchTool, FetchUrlTool, SearchGithubTool, WebSearchFetchTool
from .shell import RunShellTool
from .utility import ManageTasksTool, AskUserTool

_ALL_TOOLS: list[Tool] = [
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    DeleteFileTool(),
    ListDirTool(),
    GlobFilesTool(),
    SearchCodeTool(),
    WebSearchTool(),
    FetchUrlTool(),
    SearchGithubTool(),
    WebSearchFetchTool(),
    RunShellTool(),
    ManageTasksTool(),
    AskUserTool(),
]

AVAILABLE_TOOLS: dict[str, Tool] = {tool.name: tool for tool in _ALL_TOOLS}


def get_tools_schema() -> list[dict]:
    """Return OpenAI-compatible tool definitions for all registered tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in _ALL_TOOLS
    ]


__all__ = ["Tool", "ToolResult", "AVAILABLE_TOOLS", "get_tools_schema"]
