# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
CodeLogic MCP Server Package.

This package provides a Model Context Protocol (MCP) server implementation
that integrates with CodeLogic's dependency analysis APIs to provide
code impact analysis capabilities to AI programming assistants.
"""

import asyncio
from codelogic_mcp_server import server


def main():
    """Main entry point for the package."""
    asyncio.run(server.main())


# Optionally expose other important items at package level
__all__ = ['main', 'server']
