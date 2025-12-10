"""Entrypoint for FastMCP Cloud deployment."""

from src.main import mcp

# FastMCP cloud will look for mcp, server, or app variable
__all__ = ["mcp"]

