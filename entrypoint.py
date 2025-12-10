"""Entrypoint for FastMCP Cloud deployment."""

import asyncio
import sys
from src.main import mcp, initialize_service

# Initialize service on module import
# Use get_event_loop() to avoid conflicts with existing event loops
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running, create a task
        asyncio.create_task(initialize_service())
    else:
        # If no loop is running, run it
        loop.run_until_complete(initialize_service())
except RuntimeError:
    # No event loop exists, create and run one
    asyncio.run(initialize_service())

# FastMCP cloud will look for mcp, server, or app variable
__all__ = ["mcp"]

