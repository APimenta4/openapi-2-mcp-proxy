import argparse
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
import uvicorn


def run_server(mcp: FastMCP, defualt_port: int = 8000):
    """
    Runs the MCP server using either STDIO or SSE based on command-line arguments.

    This function parses command-line arguments to determine whether to run the server
    using standard input/output (STDIO) or as a web server (SSE) using Uvicorn.

    Args:
        mcp (FastMCP): The MCP server instance to run.
        defualt_port (int): The default port to listen on if running in SSE mode.

    Command-line Arguments:
        --stdio: If set, the server will run using stdio transport.
        --host: The hostname or IP address to bind the SSE server to (default: '0.0.0.0').
        --port: The port number for the SSE server to listen on (default: 8000).

    Behavior:
        - If `--stdio` is specified, runs the server in stdio mode.
        - Otherwise, creates a Starlette app and runs it with Uvicorn on the specified host and port.
    """
    parser = argparse.ArgumentParser(description='Run MCP Server')
    parser.add_argument('--stdio', action='store_true',
                        help='Set Transport protocol')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int,
                        default=defualt_port, help='Port to listen on')
    args = parser.parse_args()

    if args.stdio:
        mcp.run()
    else:
        starlette_app = create_starlette_app(mcp._mcp_server, debug=True)
        uvicorn.run(starlette_app, host=args.host, port=args.port)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """
    Create a Starlette application that can server the provied mcp server with SSE.
    """
    server_sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with server_sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=server_sse.handle_post_message),
        ],
    )
