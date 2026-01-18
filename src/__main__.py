"""
Entry point for running MemoBrain MCP server as a module.

Usage:
    python -m src              # Run MCP server with stdio
    python -m src --http       # Run with HTTP transport
"""

from .mcp_server import main

if __name__ == "__main__":
    main()
