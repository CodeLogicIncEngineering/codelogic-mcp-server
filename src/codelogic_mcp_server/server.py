# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Main MCP server implementation for CodeLogic integration.

This module defines the MCP server instance and its initialization process.
It handles server configuration, environment setup, and provides the main
entry point for running the server with appropriate capabilities.
"""

import os
import sys
from dotenv import load_dotenv
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from mcp.server.models import InitializationOptions

# Only load from .env file if we're not running tests
# This allows tests to set their own environment variables
if not os.environ.get('CODELOGIC_TEST_MODE'):
    load_dotenv()
    print(f"CODELOGIC_SERVER_HOST: {os.environ.get('CODELOGIC_SERVER_HOST')}", file=sys.stderr)
server = Server("codelogic-mcp-server")


async def main():
    """
    Run the MCP server with standard configuration.

    Sets up and runs the Model Context Protocol server using stdin/stdout streams
    for communication. Configures the server with appropriate capabilities and
    instructions for LLM interactions.

    Raises:
        Exception: Any errors that occur during server execution are logged and re-raised
    """
    try:
        # Import handlers module to register the decorators with our server instance
        # This import is necessary for the server to discover handlers through decorators,
        # even though we don't directly use the module in this file
        # noqa: F401 tells linters to ignore the unused import
        from . import handlers  # noqa: F401

        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="codelogic-mcp-server",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                    instructions=("When asked to modify an existing code method, invoke one or both of codelogic-method-impact and codelogic-database-impact "
                                  "mcp tools against the code provided and any methods that you are proposing changes to.  Make sure the results sent back "
                                  "from the tool are highlighted as impacts for the given method."
                                  ),
                ),
            )
    except Exception as e:
        import traceback
        print(f"Error in MCP server: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
