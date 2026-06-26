"""Entry point for the Loop Engineering MCP server."""

import asyncio
import sys
from mcp.server.stdio import stdio_server
from .server import create_server


async def _run_server():
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        server = create_server(start_scheduler=True)
        scheduler = getattr(server, "_loop_scheduler", None)
        if scheduler:
            scheduler.start()
        try:
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)
        finally:
            if scheduler:
                await scheduler.stop()


def main():
    """Run the MCP server."""
    try:
        asyncio.run(_run_server())
    except KeyboardInterrupt:
        print("\nShutting down Loop Engineering MCP server...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
