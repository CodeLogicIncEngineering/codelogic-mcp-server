# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Main handlers module for CodeLogic MCP server.

This module provides the main handler registry and routing for all CodeLogic tools.
"""

import sys
import mcp.types as types
from ..server import server
from .method_impact import handle_method_impact
from .database_impact import handle_database_impact
from .docker_agent import handle_docker_agent
from .build_info import handle_build_info
from .pipeline_helper import handle_pipeline_helper


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
            name="codelogic-docker-agent",
            description="Generate Docker agent configurations for CodeLogic scanning in CI/CD pipelines.\n"
                        "This tool provides AI models with structured data to directly modify CI/CD files.\n"
                        "Supports Jenkins, GitHub Actions, Azure DevOps, and GitLab CI with actionable file changes.",
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
        ),
        types.Tool(
            name="codelogic-build-info",
            description="This tool provides AI models with specific prompts to modify CI/CD files for build and test error reporting.\n"
                        "Includes code snippets, environment variable setup, and file modification examples.\n"
                        "Supports Git info, build logs, and metadata reporting across all major CI/CD platforms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ci_platform": {"type": "string", "description": "CI/CD platform (jenkins, github-actions, etc.) (optional)"},
                    "output_format": {
                        "type": "string",
                        "description": "Output format for the generated commands",
                        "enum": ["docker", "standalone", "jenkins", "yaml"]
                    },
                }
            },
        ),
        types.Tool(
            name="codelogic-pipeline-helper",
            description="Generate complete CI/CD pipeline configurations for CodeLogic integration.\n"
                        "This tool provides AI models with specific prompts and code snippets to modify existing CI/CD files.\n"
                        "Includes step-by-step modification guides, before/after examples, and implementation templates.\n"
                        "Supports Jenkins, GitHub Actions, Azure DevOps, and GitLab CI with actionable file modification prompts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ci_platform": {
                        "type": "string",
                        "description": "CI/CD platform for which to generate pipeline",
                        "enum": ["jenkins", "github-actions", "azure-devops", "gitlab"]
                    },
                    "agent_type": {
                        "type": "string",
                        "description": "Type of CodeLogic agent to use",
                        "enum": ["dotnet", "java", "sql", "javascript"]
                    }
                },
                "required": ["ci_platform", "agent_type"],
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
        elif name == "codelogic-docker-agent":
            return await handle_docker_agent(arguments)
        elif name == "codelogic-build-info":
            return await handle_build_info(arguments)
        elif name == "codelogic-pipeline-helper":
            return await handle_pipeline_helper(arguments)
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
