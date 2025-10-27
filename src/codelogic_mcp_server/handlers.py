# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
MCP tool handlers for the CodeLogic server integration.

This module implements the handlers for MCP tool operations.

The handlers process tool requests, interact with the CodeLogic API to gather data,
and format the results in a clear, actionable format for users.
"""

import sys
import mcp.types as types
from .server import server
from .handlers import handle_method_impact, handle_database_impact, handle_ci


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="codelogic-method-impact",
            description="Analyze impacts of modifying a specific method within a given class or type.\n"
                        "Uses CODELOGIC_WORKSPACE_NAME environment variable to determine the target workspace.\n"
                        "Recommended workflow:\n"
                        "1. Use this tool before implementing code changes\n"
                        "2. Run the tool against methods or functions that are being modified\n"
                        "3. Carefully review the impact analysis results to understand potential downstream effects\n"
                        "Particularly crucial when AI-suggested modifications are being considered.",
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "Name of the method being analyzed"},
                    "class": {"type": "string", "description": "Name of the class containing the method"},
                },
                "required": ["method", "class"],
            },
        ),
        types.Tool(
            name="codelogic-database-impact",
            description="Analyze impacts between code and database entities.\n"
                        "Uses CODELOGIC_WORKSPACE_NAME environment variable to determine the target workspace.\n"
                        "Recommended workflow:\n"
                        "1. Use this tool before implementing code or database changes\n"
                        "2. Search for the relevant database entity\n"
                        "3. Review the impact analysis to understand which code depends on this database object and vice versa\n"
                        "Particularly crucial when AI-suggested modifications are being considered or when modifying SQL code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Type of database entity to search for (column, table, or view)",
                        "enum": ["column", "table", "view"]
                    },
                    "name": {"type": "string", "description": "Name of the database entity to search for"},
                    "table_or_view": {"type": "string", "description": "Name of the table or view containing the column (required for columns only)"},
                },
                "required": ["entity_type", "name"],
            },
        ),
        types.Tool(
            name="codelogic-ci",
            description="Unified CodeLogic CI integration: generate scan (analyze) and build-info steps for CI/CD.\n"
                        "Provides AI-actionable file modifications, templates, and best practices for Jenkins, GitHub Actions, Azure DevOps, and GitLab.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "description": "Type of CodeLogic agent to configure",
                        "enum": ["dotnet", "java", "sql", "javascript"]
                    },
                    "scan_path": {"type": "string", "description": "Directory path to be scanned (e.g., /path/to/your/code)"},
                    "application_name": {"type": "string", "description": "Name of the application being scanned"},
                    "ci_platform": {
                        "type": "string",
                        "description": "CI/CD platform for which to generate configuration",
                        "enum": ["jenkins", "github-actions", "azure-devops", "gitlab", "generic"]
                    }
                },
                "required": ["agent_type", "scan_path", "application_name"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    try:
        if name == "codelogic-method-impact":
            return await handle_method_impact(arguments)
        elif name == "codelogic-database-impact":
            return await handle_database_impact(arguments)
        elif name == "codelogic-ci":
            return await handle_ci(arguments)
        else:
            sys.stderr.write(f"Unknown tool: {name}\n")
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        sys.stderr.write(f"Error handling tool call {name}: {str(e)}\n")
        error_message = f"""# Error executing tool: {name}

An error occurred while executing this tool:
```
{str(e)}
```
Please check the server logs for more details.
"""
        return [
            types.TextContent(
                type="text",
                text=error_message
            )
        ]