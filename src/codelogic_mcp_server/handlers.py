# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
MCP tool handlers for the CodeLogic server integration.

This module implements the handlers for MCP tool operations, providing two key tools:

1. codelogic-method-impact: Analyzes the potential impact of modifying a method or function
   by examining dependencies and relationships in the codebase. It processes requests,
   performs impact analysis using the CodeLogic API, and formats results for display.

2. codelogic-database-impact: Analyzes relationships between code and database entities,
   helping identify potential impacts when modifying database schemas, tables, views
   or columns. It examines both direct and indirect dependencies to surface risks.

The handlers process tool requests, interact with the CodeLogic API to gather impact data,
and format the results in a clear, actionable format for users.
"""

import json
import os
import sys
from .server import server
import mcp.types as types
from .utils import extract_nodes, extract_relationships, get_mv_id, get_method_nodes, get_impact, find_node_by_id, search_database_entity, process_database_entity_impact, generate_combined_database_report, find_api_endpoints
import time
from datetime import datetime
import tempfile

DEBUG_MODE = os.getenv("CODELOGIC_DEBUG_MODE", "false").lower() == "true"

# Use a user-specific temporary directory for logs to avoid permission issues when running via uvx
# Only create the directory when debug mode is enabled
LOGS_DIR = os.path.join(tempfile.gettempdir(), "codelogic-mcp-server")
if DEBUG_MODE:
    os.makedirs(LOGS_DIR, exist_ok=True)


def ensure_logs_dir():
    """Ensure the logs directory exists when needed for debug mode."""
    if DEBUG_MODE:
        os.makedirs(LOGS_DIR, exist_ok=True)


def write_json_to_file(file_path, data):
    """Write JSON data to a file with improved formatting."""
    ensure_logs_dir()
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, separators=(", ", ": "), ensure_ascii=False, sort_keys=True)


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
                        "Returns specific file paths, line numbers, and exact code modifications.\n"
                        "Supports Jenkins, GitHub Actions, Azure DevOps, and GitLab CI with actionable file changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "description": "Type of CodeLogic agent to configure",
                        "enum": ["dotnet", "java", "sql", "typescript"]
                    },
                    "scan_path": {"type": "string", "description": "Directory path to be scanned (e.g., /path/to/your/code)"},
                    "application_name": {"type": "string", "description": "Name of the application being scanned"},
                    "scan_space_name": {"type": "string", "description": "Name of the scan space (e.g., 'Development', 'Production')"},
                    "ci_platform": {
                        "type": "string",
                        "description": "CI/CD platform for which to generate configuration",
                        "enum": ["jenkins", "github-actions", "azure-devops", "gitlab", "generic"]
                    },
                    "include_build_info": {"type": "boolean", "description": "Whether to include build information sending capabilities", "default": True},
                },
                "required": ["agent_type", "scan_path", "application_name"],
            },
        ),
        types.Tool(
            name="codelogic-build-info",
            description="Generate build information and send commands for CodeLogic integration.\n"
                        "This tool provides AI models with specific prompts to modify CI/CD files for build information collection.\n"
                        "Includes code snippets, environment variable setup, and file modification examples.\n"
                        "Supports Git info, build logs, and metadata collection across all major CI/CD platforms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "build_type": {
                        "type": "string",
                        "description": "Type of build information to send",
                        "enum": ["git-info", "build-log", "metadata", "all"]
                    },
                    "log_file_path": {"type": "string", "description": "Path to build log file (optional)"},
                    "job_name": {"type": "string", "description": "CI/CD job name (optional)"},
                    "build_number": {"type": "string", "description": "Build number (optional)"},
                    "build_status": {"type": "string", "description": "Build status (SUCCESS, FAILURE, etc.) (optional)"},
                    "ci_platform": {"type": "string", "description": "CI/CD platform (jenkins, github-actions, etc.) (optional)"},
                    "output_format": {
                        "type": "string",
                        "description": "Output format for the generated commands",
                        "enum": ["docker", "standalone", "jenkins", "yaml"]
                    },
                },
                "required": ["build_type"],
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
                        "enum": ["dotnet", "java", "sql", "typescript"]
                    },
                    "scan_triggers": {
                        "type": "array",
                        "description": "Git branches or events that should trigger scanning",
                        "items": {"type": "string"}
                    },
                    "include_notifications": {"type": "boolean", "description": "Whether to include notification configurations", "default": True},
                    "scan_space_strategy": {
                        "type": "string",
                        "description": "Strategy for managing scan spaces",
                        "enum": ["unique-per-branch", "shared-development", "environment-based"]
                    },
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


async def handle_method_impact(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-method-impact tool for method/function analysis"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    method_name = arguments.get("method")
    class_name = arguments.get("class")
    if class_name and "." in class_name:
        class_name = class_name.split(".")[-1]

    if not (method_name):
        sys.stderr.write("Method must be provided\n")
        raise ValueError("Method must be provided")

    mv_id = get_mv_id(os.getenv("CODELOGIC_WORKSPACE_NAME") or "")

    start_time = time.time()
    nodes = get_method_nodes(mv_id, method_name)
    end_time = time.time()
    duration = end_time - start_time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if DEBUG_MODE:
        ensure_logs_dir()
        with open(os.path.join(LOGS_DIR, "timing_log.txt"), "a") as log_file:
            log_file.write(f"{timestamp} - get_method_nodes for method '{method_name}' in class '{class_name}' took {duration:.4f} seconds\n")

    # Check if nodes is empty due to timeout or server error
    if not nodes:
        error_message = f"""# Unable to Analyze Method: `{method_name}`

## Error
The request to retrieve method information from the CodeLogic server timed out or failed (504 Gateway Timeout).

## Possible causes:
1. The CodeLogic server is under heavy load
2. Network connectivity issues between the MCP server and CodeLogic
3. The method name provided (`{method_name}`) doesn't exist in the codebase

## Recommendations:
1. Try again in a few minutes
2. Verify the method name is correct
3. Check your connection to the CodeLogic server at: {os.getenv('CODELOGIC_SERVER_HOST')}
4. If the problem persists, contact your CodeLogic administrator
"""
        return [
            types.TextContent(
                type="text",
                text=error_message
            )
        ]

    if class_name:
        node = next((n for n in nodes if f"|{class_name}|" in n['identity'] or f"|{class_name}.class|" in n['identity']), None)
        if not node:
            raise ValueError(f"No matching class found for {class_name}")
    else:
        node = nodes[0]

    start_time = time.time()
    impact = get_impact(node['properties']['id'])
    end_time = time.time()
    duration = end_time - start_time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if DEBUG_MODE:
        ensure_logs_dir()
        with open(os.path.join(LOGS_DIR, "timing_log.txt"), "a") as log_file:
            log_file.write(f"{timestamp} - get_impact for node '{node['name']}' took {duration:.4f} seconds\n")
        method_file_name = os.path.join(LOGS_DIR, f"impact_data_method_{class_name}_{method_name}.json") if class_name else os.path.join(LOGS_DIR, f"impact_data_method_{method_name}.json")
        write_json_to_file(method_file_name, json.loads(impact))
    impact_data = json.loads(impact)
    nodes = extract_nodes(impact_data)
    relationships = extract_relationships(impact_data)

    # Better method to find the target method node with complexity information
    target_node = None

    # Support both Java and DotNet method entities
    method_entity_types = ['JavaMethodEntity', 'DotNetMethodEntity']
    method_nodes = []

    # First look for method nodes of any supported language
    for entity_type in method_entity_types:
        language_method_nodes = [n for n in nodes if n['primaryLabel'] == entity_type and method_name.lower() in n['name'].lower()]
        method_nodes.extend(language_method_nodes)

    # If we have class name, further filter to find nodes that contain it
    if class_name:
        class_filtered_nodes = [n for n in method_nodes if class_name.lower() in n['identity'].lower()]
        if class_filtered_nodes:
            method_nodes = class_filtered_nodes

    # Find the node with complexity metrics (prefer this)
    for n in method_nodes:
        if n['properties'].get('statistics.cyclomaticComplexity') is not None:
            target_node = n
            break

    # If not found, take the first method node
    if not target_node and method_nodes:
        target_node = method_nodes[0]

    # Last resort: fall back to the original node (which might not have metrics)
    if not target_node:
        target_node = next((n for n in nodes if n['properties'].get('id') == node['properties'].get('id')), None)

    # Extract key metrics
    complexity = target_node['properties'].get('statistics.cyclomaticComplexity', 'N/A') if target_node else 'N/A'
    instruction_count = target_node['properties'].get('statistics.instructionCount', 'N/A') if target_node else 'N/A'

    # Extract code owners and reviewers
    code_owners = target_node['properties'].get('codelogic.owners', []) if target_node else []
    code_reviewers = target_node['properties'].get('codelogic.reviewers', []) if target_node else []

    # If target node doesn't have owners/reviewers, try to find them from the class or file node
    if not code_owners or not code_reviewers:
        class_node = None
        if class_name:
            class_node = next((n for n in nodes if n['primaryLabel'].endswith('ClassEntity') and class_name.lower() in n['name'].lower()), None)

        if class_node:
            if not code_owners:
                code_owners = class_node['properties'].get('codelogic.owners', [])
            if not code_reviewers:
                code_reviewers = class_node['properties'].get('codelogic.reviewers', [])

    # Identify dependents (systems that depend on this method)
    dependents = []

    for rel in impact_data.get('data', {}).get('relationships', []):
        start_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel['startId'])
        end_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel['endId'])

        if start_node and end_node and end_node['id'] == node['properties'].get('id'):
            # This is an incoming relationship (dependent)
            dependents.append({
                "name": start_node.get('name'),
                "type": start_node.get('primaryLabel'),
                "relationship": rel.get('type')
            })

    # Identify applications that depend on this method
    affected_applications = set()
    app_nodes = [n for n in nodes if n['primaryLabel'] == 'Application']
    app_id_to_name = {app['id']: app['name'] for app in app_nodes}

    # Add all applications found in the impact analysis as potentially affected
    for app in app_nodes:
        affected_applications.add(app['name'])

    # Map nodes to their applications via groupIds (Java approach)
    for node_item in nodes:
        if 'groupIds' in node_item['properties']:
            for group_id in node_item['properties']['groupIds']:
                if group_id in app_id_to_name:
                    affected_applications.add(app_id_to_name[group_id])

    # Count direct and indirect application dependencies
    app_dependencies = {}

    # Check both REFERENCES_GROUP and GROUPS relationships
    for rel in impact_data.get('data', {}).get('relationships', []):
        if rel.get('type') in ['REFERENCES_GROUP', 'GROUPS']:
            start_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel['startId'])
            end_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel['endId'])

            # For GROUPS relationships - application groups a component
            if rel.get('type') == 'GROUPS' and start_node and start_node.get('primaryLabel') == 'Application':
                app_name = start_node.get('name')
                affected_applications.add(app_name)

            # For REFERENCES_GROUP - one application depends on another
            if rel.get('type') == 'REFERENCES_GROUP' and start_node and end_node and start_node.get('primaryLabel') == 'Application' and end_node.get('primaryLabel') == 'Application':
                app_name = start_node.get('name')
                depends_on = end_node.get('name')
                if app_name:
                    affected_applications.add(app_name)
                    if app_name not in app_dependencies:
                        app_dependencies[app_name] = []
                    app_dependencies[app_name].append(depends_on)

    # Use the new utility function to detect API endpoints and controllers
    endpoint_nodes, rest_endpoints, api_controllers, endpoint_dependencies = find_api_endpoints(nodes, impact_data.get('data', {}).get('relationships', []))

    # Format nodes with metrics in markdown table format
    nodes_table = "| Name | Type | Complexity | Instruction Count | Method Count | Outgoing Refs | Incoming Refs |\n"
    nodes_table += "|------|------|------------|-------------------|-------------|---------------|---------------|\n"

    for node_item in nodes:
        name = node_item['name']
        node_type = node_item['primaryLabel']
        node_complexity = node_item['properties'].get('statistics.cyclomaticComplexity', 'N/A')
        node_instructions = node_item['properties'].get('statistics.instructionCount', 'N/A')
        node_methods = node_item['properties'].get('statistics.methodCount', 'N/A')
        outgoing_refs = node_item['properties'].get('statistics.outgoingExternalReferenceTotal', 'N/A')
        incoming_refs = node_item['properties'].get('statistics.incomingExternalReferenceTotal', 'N/A')

        # Mark high complexity items
        complexity_str = str(node_complexity)
        if node_complexity not in ('N/A', None) and float(node_complexity) > 10:
            complexity_str = f"**{complexity_str}** ⚠️"

        nodes_table += f"| {name} | {node_type} | {complexity_str} | {node_instructions} | {node_methods} | {outgoing_refs} | {incoming_refs} |\n"

    # Format relationships in a more structured way for table display
    relationship_rows = []

    for rel in impact_data.get('data', {}).get('relationships', []):
        start_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel['startId'])
        end_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel['endId'])

        if start_node and end_node:
            relationship_rows.append({
                "type": rel.get('type', 'UNKNOWN'),
                "source": start_node.get('name', 'Unknown'),
                "source_type": start_node.get('primaryLabel', 'Unknown'),
                "target": end_node.get('name', 'Unknown'),
                "target_type": end_node.get('primaryLabel', 'Unknown')
            })

    # Also keep the relationships grouped by type for reference
    relationships_by_type = {}
    for rel in relationships:
        rel_parts = rel.split(" (")
        if len(rel_parts) >= 2:
            source = rel_parts[0]
            rel_type = "(" + rel_parts[1]
            if rel_type not in relationships_by_type:
                relationships_by_type[rel_type] = []
            relationships_by_type[rel_type].append(source)

    # Build the markdown output
    impact_description = f"""# Impact Analysis for Method: `{method_name}`

## Guidelines for AI
- Pay special attention to methods with Cyclomatic Complexity over 10 as they represent higher risk
- Consider the cross-application dependencies when making changes
- Prioritize testing for components that directly depend on this method
- Suggest refactoring when complexity metrics indicate poor maintainability
- Consider the full relationship map to understand cascading impacts
- Highlight REST API endpoints and external dependencies that may be affected by changes

## Summary
- **Method**: `{method_name}`
- **Class**: `{class_name or 'N/A'}`
"""

    # Add code ownership information if available
    if code_owners:
        impact_description += f"- **Code Owners**: {', '.join(code_owners)}\n"
    if code_reviewers:
        impact_description += f"- **Code Reviewers**: {', '.join(code_reviewers)}\n"

    impact_description += f"- **Complexity**: {complexity}\n"
    impact_description += f"- **Instruction Count**: {instruction_count}\n"
    impact_description += f"- **Affected Applications**: {len(affected_applications)}\n"

    # Add affected REST endpoints to the Summary section
    if endpoint_nodes:
        impact_description += "\n### Affected REST Endpoints\n"
        for endpoint in endpoint_nodes:
            impact_description += f"- `{endpoint['http_verb']} {endpoint['path']}`\n"

    # Start the Risk Assessment section
    impact_description += "\n## Risk Assessment\n"

    # Add complexity risk assessment
    if complexity not in ('N/A', None) and float(complexity) > 10:
        impact_description += f"⚠️ **Warning**: Cyclomatic complexity of {complexity} exceeds threshold of 10\n\n"
    else:
        impact_description += "✅ Complexity is within acceptable limits\n\n"

    # Add cross-application risk assessment
    if len(affected_applications) > 1:
        impact_description += f"⚠️ **Cross-Application Dependency**: This method is used by {len(affected_applications)} applications:\n"
        for app in sorted(affected_applications):
            deps = app_dependencies.get(app, [])
            if deps:
                impact_description += f"- `{app}` (depends on: {', '.join([f'`{d}`' for d in deps])})\n"
            else:
                impact_description += f"- `{app}`\n"
        impact_description += "\nChanges to this method may cause widespread impacts across multiple applications. Consider careful testing across all affected systems.\n"
    else:
        impact_description += "✅ Method is used within a single application context\n"

    # Add REST API risk assessment (now as a subsection of Risk Assessment)
    if rest_endpoints or api_controllers or endpoint_nodes:
        impact_description += "\n### REST API Risk Assessment\n"
        impact_description += "⚠️ **API Impact Alert**: This method affects REST endpoints or API controllers\n"

        if rest_endpoints:
            impact_description += "\n#### REST Methods with Annotations\n"
            for endpoint in rest_endpoints:
                impact_description += f"- `{endpoint['name']}` ({endpoint['annotation']})\n"

        if api_controllers:
            impact_description += "\n#### Affected API Controllers\n"
            for controller in api_controllers:
                impact_description += f"- `{controller['name']}` ({controller['type']})\n"

        # Add endpoint dependencies as a subsection of Risk Assessment
        if endpoint_dependencies:
            impact_description += "\n### REST API Dependencies\n"
            impact_description += "⚠️ **Chained API Risk**: Changes may affect multiple interconnected endpoints\n\n"
            for dep in endpoint_dependencies:
                impact_description += f"- `{dep['source']}` depends on `{dep['target']}`\n"

        # Add API Change Risk Factors as a subsection of Risk Assessment
        impact_description += """
### API Change Risk Factors
- Changes may affect external consumers and services
- Consider versioning strategy for breaking changes
- API contract changes require thorough documentation
- Update API tests and client libraries as needed
- Consider backward compatibility requirements
- **Chained API calls**: Changes may have cascading effects across multiple endpoints
- **Cross-application impact**: API changes could affect dependent systems
"""
    else:
        impact_description += "\n### REST API Risk Assessment\n"
        impact_description += "✅ No direct impact on REST endpoints or API controllers detected\n"

    # Ownership-based consultation recommendation
    if code_owners or code_reviewers:
        impact_description += "\n### Code Ownership\n"
        if code_owners:
            impact_description += f"👤 **Code Owners**: Changes to this code should be reviewed by: {', '.join(code_owners)}\n"
        if code_reviewers:
            impact_description += f"👁️ **Preferred Reviewers**: Consider getting reviews from: {', '.join(code_reviewers)}\n"

        if code_owners:
            impact_description += "\nConsult with the code owners before making significant changes to ensure alignment with original design intent.\n"

    impact_description += f"""
## Method Impact
This analysis focuses on systems that depend on `{method_name}`. Modifying this method could affect these dependents:

"""

    if dependents:
        for dep in dependents:
            impact_description += f"- `{dep['name']}` ({dep['type']}) via `{dep['relationship']}`\n"
    else:
        impact_description += "No components directly depend on this method. The change appears to be isolated.\n"

    impact_description += f"\n## Detailed Node Metrics\n{nodes_table}\n"

    # Create relationship table
    relationship_table = "| Relationship Type | Source | Source Type | Target | Target Type |\n"
    relationship_table += "|------------------|--------|-------------|--------|------------|\n"

    for row in relationship_rows:
        # Highlight relationships involving our target method
        highlight = ""
        if (method_name.lower() in row["source"].lower() or method_name.lower() in row["target"].lower()):
            if class_name and (class_name.lower() in row["source"].lower() or class_name.lower() in row["target"].lower()):
                highlight = "**"  # Bold the important relationships

        relationship_table += f"| {highlight}{row['type']}{highlight} | {highlight}{row['source']}{highlight} | {row['source_type']} | {highlight}{row['target']}{highlight} | {row['target_type']} |\n"

    impact_description += "\n## Relationship Map\n"
    impact_description += relationship_table

    # Add application dependency visualization if multiple applications are affected
    if len(affected_applications) > 1:
        impact_description += "\n## Application Dependency Graph\n"
        impact_description += "```\n"
        for app in sorted(affected_applications):
            deps = app_dependencies.get(app, [])
            if deps:
                impact_description += f"{app} → {' → '.join(deps)}\n"
            else:
                impact_description += f"{app} (no dependencies)\n"
        impact_description += "```\n"

    return [
        types.TextContent(
            type="text",
            text=impact_description,
        )
    ]


async def handle_database_impact(arguments: dict | None) -> list[types.TextContent]:
    """Handle the database-impact tool for database entity analysis"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    entity_type = arguments.get("entity_type")
    name = arguments.get("name")
    table_or_view = arguments.get("table_or_view")

    if not entity_type or not name:
        sys.stderr.write("Entity type and name must be provided\n")
        raise ValueError("Entity type and name must be provided")

    if entity_type not in ["column", "table", "view"]:
        sys.stderr.write(f"Invalid entity type: {entity_type}. Must be column, table, or view.\n")
        raise ValueError(f"Invalid entity type: {entity_type}")

    # Verify table_or_view is provided for columns
    if entity_type == "column" and not table_or_view:
        sys.stderr.write("Table or view name must be provided for column searches\n")
        raise ValueError("Table or view name must be provided for column searches")

    # Search for the database entity
    start_time = time.time()
    search_results = await search_database_entity(entity_type, name, table_or_view)
    end_time = time.time()
    duration = end_time - start_time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if DEBUG_MODE:
        ensure_logs_dir()
        with open(os.path.join(LOGS_DIR, "timing_log.txt"), "a") as log_file:
            log_file.write(f"{timestamp} - search_database_entity for {entity_type} '{name}' took {duration:.4f} seconds\n")

    if not search_results:
        table_view_text = f" in {table_or_view}" if table_or_view else ""
        return [
            types.TextContent(
                type="text",
                text=f"# No {entity_type}s found matching '{name}'{table_view_text}\n\nNo database {entity_type}s were found matching the name '{name}'"
                     + (f" in {table_or_view}" if table_or_view else "") + "."
            )
        ]

    # Process each entity and get its impact
    all_impacts = []
    for entity in search_results[:5]:  # Limit to 5 to avoid excessive processing
        entity_id = entity.get("id")
        entity_name = entity.get("name")
        entity_schema = entity.get("schema", "Unknown")

        try:
            start_time = time.time()
            impact = get_impact(entity_id)
            end_time = time.time()
            duration = end_time - start_time
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if DEBUG_MODE:
                ensure_logs_dir()
                with open(os.path.join(LOGS_DIR, "timing_log.txt"), "a") as log_file:
                    log_file.write(f"{timestamp} - get_impact for {entity_type} '{entity_name}' took {duration:.4f} seconds\n")
                write_json_to_file(os.path.join(LOGS_DIR, f"impact_data_{entity_type}_{entity_name}.json"), json.loads(impact))
            impact_data = json.loads(impact)
            impact_summary = process_database_entity_impact(
                impact_data, entity_type, entity_name, entity_schema
            )
            all_impacts.append(impact_summary)
        except Exception as e:
            sys.stderr.write(f"Error getting impact for {entity_type} '{entity_name}': {str(e)}\n")

    # Combine all impacts into a single report
    combined_report = generate_combined_database_report(
        entity_type, name, table_or_view, search_results, all_impacts
    )

    return [
        types.TextContent(
            type="text",
            text=combined_report
        )
    ]


async def handle_docker_agent(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-docker-agent tool for DevOps Docker agent configuration"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    agent_type = arguments.get("agent_type")
    scan_path = arguments.get("scan_path")
    application_name = arguments.get("application_name")
    scan_space_name = arguments.get("scan_space_name", "Development")
    ci_platform = arguments.get("ci_platform", "generic")
    include_build_info = arguments.get("include_build_info", True)

    # Validate required parameters
    if not agent_type or not scan_path or not application_name:
        sys.stderr.write("Agent type, scan path, and application name are required\n")
        raise ValueError("Agent type, scan path, and application name are required")

    # Validate agent type
    valid_agent_types = ["dotnet", "java", "sql", "typescript"]
    if agent_type not in valid_agent_types:
        sys.stderr.write(f"Invalid agent type: {agent_type}. Must be one of: {', '.join(valid_agent_types)}\n")
        raise ValueError(f"Invalid agent type: {agent_type}. Must be one of: {', '.join(valid_agent_types)}")

    # Validate CI platform
    valid_ci_platforms = ["jenkins", "github-actions", "azure-devops", "gitlab", "generic"]
    if ci_platform not in valid_ci_platforms:
        sys.stderr.write(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}\n")
        raise ValueError(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}")

    # Get server configuration
    server_host = os.getenv("CODELOGIC_SERVER_HOST", "https://your-instance.app.codelogic.com")
    
    # Generate Docker agent configuration based on agent type
    agent_config = generate_docker_agent_config(
        agent_type, scan_path, application_name, scan_space_name, 
        ci_platform, include_build_info, server_host
    )

    return [
        types.TextContent(
            type="text",
            text=agent_config
        )
    ]


async def handle_build_info(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-build-info tool for build information management"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    build_type = arguments.get("build_type")
    log_file_path = arguments.get("log_file_path")
    job_name = arguments.get("job_name")
    build_number = arguments.get("build_number")
    build_status = arguments.get("build_status")
    ci_platform = arguments.get("ci_platform")
    output_format = arguments.get("output_format", "docker")

    # Validate required parameters
    if not build_type:
        sys.stderr.write("Build type is required\n")
        raise ValueError("Build type is required")

    # Validate build type
    valid_build_types = ["git-info", "build-log", "metadata", "all"]
    if build_type not in valid_build_types:
        sys.stderr.write(f"Invalid build type: {build_type}. Must be one of: {', '.join(valid_build_types)}\n")
        raise ValueError(f"Invalid build type: {build_type}. Must be one of: {', '.join(valid_build_types)}")

    # Validate output format
    valid_output_formats = ["docker", "standalone", "jenkins", "yaml"]
    if output_format not in valid_output_formats:
        sys.stderr.write(f"Invalid output format: {output_format}. Must be one of: {', '.join(valid_output_formats)}\n")
        raise ValueError(f"Invalid output format: {output_format}. Must be one of: {', '.join(valid_output_formats)}")

    # Generate build info configuration
    build_info_config = generate_build_info_config(
        build_type, log_file_path, job_name, build_number, 
        build_status, ci_platform, output_format
    )

    return [
        types.TextContent(
            type="text",
            text=build_info_config
        )
    ]


async def handle_pipeline_helper(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-pipeline-helper tool for complete CI/CD pipeline configuration"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    ci_platform = arguments.get("ci_platform")
    agent_type = arguments.get("agent_type")
    scan_triggers = arguments.get("scan_triggers", ["main", "develop"])
    include_notifications = arguments.get("include_notifications", True)
    scan_space_strategy = arguments.get("scan_space_strategy", "unique-per-branch")

    # Validate required parameters
    if not ci_platform or not agent_type:
        sys.stderr.write("CI platform and agent type are required\n")
        raise ValueError("CI platform and agent type are required")

    # Validate CI platform
    valid_ci_platforms = ["jenkins", "github-actions", "azure-devops", "gitlab"]
    if ci_platform not in valid_ci_platforms:
        sys.stderr.write(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}\n")
        raise ValueError(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}")

    # Validate agent type
    valid_agent_types = ["dotnet", "java", "sql", "typescript"]
    if agent_type not in valid_agent_types:
        sys.stderr.write(f"Invalid agent type: {agent_type}. Must be one of: {', '.join(valid_agent_types)}\n")
        raise ValueError(f"Invalid agent type: {agent_type}. Must be one of: {', '.join(valid_agent_types)}")

    # Validate scan space strategy
    valid_strategies = ["unique-per-branch", "shared-development", "environment-based"]
    if scan_space_strategy not in valid_strategies:
        sys.stderr.write(f"Invalid scan space strategy: {scan_space_strategy}. Must be one of: {', '.join(valid_strategies)}\n")
        raise ValueError(f"Invalid scan space strategy: {scan_space_strategy}. Must be one of: {', '.join(valid_strategies)}")

    # Generate pipeline configuration
    pipeline_config = generate_pipeline_config(
        ci_platform, agent_type, scan_triggers, 
        include_notifications, scan_space_strategy
    )

    return [
        types.TextContent(
            type="text",
            text=pipeline_config
        )
    ]


def generate_docker_agent_config(agent_type, scan_path, application_name, scan_space_name, ci_platform, include_build_info, server_host):
    """Generate Docker agent configuration with AI-actionable prompts for CI/CD file modification"""
    
    # Agent type mappings
    agent_images = {
        "dotnet": "codelogic_dotnet",
        "java": "codelogic_java", 
        "sql": "codelogic_sql",
        "typescript": "codelogic_typescript"
    }
    
    agent_image = agent_images.get(agent_type, "codelogic_dotnet")
    
    # Generate structured data for AI models to directly modify CI/CD files
    structured_config = {
        "target_files": get_target_files(ci_platform),
        "environment_variables": {
            "CODELOGIC_HOST": server_host,
            "AGENT_UUID": "your-agent-uuid",
            "AGENT_PASSWORD": "your-agent-password"
        },
        "docker_command": generate_docker_command(agent_type, scan_path, application_name, scan_space_name, server_host, agent_image),
        "file_modifications": generate_file_modifications(ci_platform, agent_type, scan_path, application_name, scan_space_name, server_host, agent_image),
        "setup_instructions": generate_setup_instructions(ci_platform),
        "validation_checks": generate_validation_checks(ci_platform)
    }
    
    config = f"""# CodeLogic {agent_type.upper()} Docker Agent - AI File Modification Guide

## 🎯 AI Model Instructions

**Use the structured data below to directly modify CI/CD files in the repository.**

### Target Files to Modify
{format_target_files(structured_config['target_files'])}

### Environment Variables to Add
{format_environment_variables(structured_config['environment_variables'])}

### Docker Command Template
```bash
{structured_config['docker_command']}
```

### Specific File Modifications
{format_file_modifications(structured_config['file_modifications'])}

### Setup Instructions
{format_setup_instructions(structured_config['setup_instructions'])}

### Validation Checks
{format_validation_checks(structured_config['validation_checks'])}

## 🔧 Environment Variable Usage Guide

### For CodeLogic Analyze Operations:
- **Required**: `CODELOGIC_HOST`, `AGENT_UUID`, `AGENT_PASSWORD`
- **Do NOT include**: `JOB_NAME`, `BUILD_NUMBER`, `GIT_COMMIT`, `GIT_BRANCH`
- **Purpose**: Basic authentication for code scanning

### For CodeLogic Build Info Operations:
- **Required**: `CODELOGIC_HOST`, `AGENT_UUID`, `AGENT_PASSWORD`
- **Optional**: `JOB_NAME`, `BUILD_NUMBER`, `BUILD_STATUS`, `GIT_COMMIT`, `GIT_BRANCH`
- **Purpose**: Send build metadata and context to CodeLogic

### Important Notes:
- **Analyze operations** only need basic authentication
- **Build info operations** need additional metadata variables
- **Do NOT mix** environment variables between operation types
- **Each operation** has specific environment variable requirements

## 📋 Structured Data for AI Processing

```json
{json.dumps(structured_config, indent=2)}
```

"""

    # Add platform-specific configurations
    if ci_platform == "jenkins":
        config += generate_jenkins_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host)
    elif ci_platform == "github-actions":
        config += generate_github_actions_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host)
    elif ci_platform == "azure-devops":
        config += generate_azure_devops_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host)
    elif ci_platform == "gitlab":
        config += generate_gitlab_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host)
    else:
        config += generate_generic_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host)

    # Add build info section if requested
    if include_build_info:
        config += f"""

## Build Information Integration

To send build information to CodeLogic, add this step after your scan:

```bash
# Send build information
docker run --rm \\
    --env CODELOGIC_HOST="{server_host}" \\
    --env AGENT_UUID="${{AGENT_UUID}}" \\
    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
    --volume "{scan_path}:/scan" \\
    --volume "${{PWD}}/logs:/log_file_path" \\
    {server_host}/{agent_image}:latest send_build_info \\
    --log-file="/log_file_path/build.log"
```

## Best Practices

1. **Scan Space Management**: Use unique scan spaces per branch to avoid conflicts
2. **Error Handling**: Always use `--rescan` and `--expunge-scan-sessions` for CI/CD
3. **Security**: Store credentials as environment variables, never in code
4. **Performance**: Use `--pull always` to ensure latest agent version
5. **Logging**: Mount log directories for build information collection

## Troubleshooting

- **Permission Issues**: Ensure Docker has access to scan directory
- **Network Issues**: Verify CodeLogic server connectivity
- **Credential Issues**: Check AGENT_UUID and AGENT_PASSWORD are correct
- **Scan Failures**: Review agent logs for specific error messages
"""

    return config


def get_target_files(ci_platform):
    """Get target files for each CI/CD platform"""
    platform_files = {
        "jenkins": ["Jenkinsfile", ".jenkins/pipeline.groovy"],
        "github-actions": [".github/workflows/*.yml"],
        "azure-devops": ["azure-pipelines.yml", ".azure-pipelines/*.yml"],
        "gitlab": [".gitlab-ci.yml"],
        "generic": ["*.yml", "*.yaml", "Jenkinsfile", "Dockerfile"]
    }
    return platform_files.get(ci_platform, platform_files["generic"])


def generate_docker_command(agent_type, scan_path, application_name, scan_space_name, server_host, agent_image):
    """Generate the Docker command template with proper environment variable handling"""
    return f"""# CodeLogic Analyze Operation - Docker Command

## Required Environment Variables (Analyze Operation)
- `CODELOGIC_HOST`: {server_host}
- `AGENT_UUID`: your-agent-uuid  
- `AGENT_PASSWORD`: your-agent-password

## Docker Command
```bash
docker run --pull always --rm --interactive \\
    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
    --env AGENT_UUID="${{AGENT_UUID}}" \\
    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
    --volume "{scan_path}:/scan" \\
    {server_host}/{agent_image}:latest analyze \\
    --application "{application_name}" \\
    --path /scan \\
    --scan-space-name "{scan_space_name}" \\
    --rescan \\
    --expunge-scan-sessions
```

## Important Notes
- **Only 3 environment variables are needed for the analyze operation**
- **Do NOT include JOB_NAME, BUILD_NUMBER, GIT_COMMIT, or GIT_BRANCH for analyze**
- **These additional variables are only used for build info operations**
- **Build-related environment variables are only needed for send_build_info operations**"""


def generate_file_modifications(ci_platform, agent_type, scan_path, application_name, scan_space_name, server_host, agent_image):
    """Generate specific file modifications for each platform"""
    modifications = {
        "jenkins": {
            "file": "Jenkinsfile",
            "modifications": [
                {
                    "type": "add_environment",
                    "location": "environment block",
                    "content": f"""environment {{
    CODELOGIC_HOST = '{server_host}'
    AGENT_UUID = credentials('codelogic-agent-uuid')
    AGENT_PASSWORD = credentials('codelogic-agent-password')
}}"""
                },
                {
                    "type": "add_stage",
                    "location": "after build stages",
                    "content": f"""stage('CodeLogic Scan') {{
    when {{
        anyOf {{
            branch 'main'
            branch 'develop'
            branch 'feature/*'
        }}
    }}
    steps {{
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {{
            // CodeLogic analyze operation - only needs basic auth environment variables
            // Do NOT include JOB_NAME, BUILD_NUMBER, GIT_COMMIT, or GIT_BRANCH for analyze
            sh '''
                docker run --pull always --rm --interactive \\
                    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                    --env AGENT_UUID="${{AGENT_UUID}}" \\
                    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                    --volume "${{WORKSPACE}}:/scan" \\
                    ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest analyze \\
                    --application "{application_name}" \\
                    --path /scan \\
                    --scan-space-name "{scan_space_name}" \\
                    --rescan \\
                    --expunge-scan-sessions
            '''
        }}
    }}
}}"""
                }
            ]
        },
        "github-actions": {
            "file": ".github/workflows/codelogic-scan.yml",
            "modifications": [
                {
                    "type": "create_file",
                    "content": f"""name: CodeLogic Scan

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main ]

jobs:
  codelogic-scan:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
      
    - name: CodeLogic Scan
      run: |
        docker run --pull always --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest analyze \\
          --application "{application_name}" \\
          --path /scan \\
          --scan-space-name "{scan_space_name}" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true"""
                }
            ]
        }
    }
    return modifications.get(ci_platform, {})


def generate_setup_instructions(ci_platform):
    """Generate setup instructions for each platform"""
    instructions = {
        "jenkins": [
            "Go to Jenkins → Manage Jenkins → Manage Credentials",
            "Add Secret Text credentials: codelogic-agent-uuid, codelogic-agent-password",
            "Install Docker Pipeline Plugin if not already installed"
        ],
        "github-actions": [
            "Go to repository Settings → Secrets and variables → Actions",
            "Add repository secrets: CODELOGIC_HOST, AGENT_UUID, AGENT_PASSWORD",
            "Ensure Docker is available in runner (default for ubuntu-latest)"
        ],
        "azure-devops": [
            "Go to pipeline variables and add: codelogicAgentUuid, codelogicAgentPassword",
            "Mark variables as secret",
            "Ensure Docker task is available"
        ],
        "gitlab": [
            "Go to Settings → CI/CD → Variables",
            "Add variables: AGENT_UUID, AGENT_PASSWORD",
            "Mark as protected and masked",
            "Ensure Docker-in-Docker is enabled"
        ]
    }
    return instructions.get(ci_platform, [])


def generate_validation_checks(ci_platform):
    """Generate validation checks for each platform"""
    checks = {
        "jenkins": [
            "Verify credentials are properly configured",
            "Test Docker command manually",
            "Check Jenkins agent has Docker access"
        ],
        "github-actions": [
            "Verify secrets are set correctly",
            "Test workflow runs without errors",
            "Check Docker is available in runner"
        ],
        "azure-devops": [
            "Verify variables are marked as secret",
            "Test Docker task execution",
            "Check pipeline permissions"
        ],
        "gitlab": [
            "Verify variables are protected and masked",
            "Test Docker-in-Docker functionality",
            "Check pipeline permissions"
        ]
    }
    return checks.get(ci_platform, [])


def format_target_files(target_files):
    """Format target files for display"""
    if isinstance(target_files, list):
        return "\n".join([f"- `{file}`" for file in target_files])
    return f"- `{target_files}`"


def format_environment_variables(env_vars):
    """Format environment variables for display"""
    return "\n".join([f"- `{key}`: {value}" for key, value in env_vars.items()])


def format_file_modifications(modifications):
    """Format file modifications for display"""
    if not modifications:
        return "No specific modifications required."
    
    result = []
    for mod in modifications.get('modifications', []):
        result.append(f"**{mod['type'].replace('_', ' ').title()}**: {mod.get('location', 'N/A')}")
        result.append(f"```\n{mod['content']}\n```")
    
    return "\n".join(result)


def format_setup_instructions(instructions):
    """Format setup instructions for display"""
    return "\n".join([f"{i+1}. {instruction}" for i, instruction in enumerate(instructions)])


def format_validation_checks(checks):
    """Format validation checks for display"""
    return "\n".join([f"- {check}" for check in checks])


def generate_jenkins_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host):
    """Generate Jenkins-specific configuration with AI modification prompts"""
    return f"""
### 🎯 Jenkins File Modification Guide

**AI Prompt: "Modify the Jenkinsfile to add CodeLogic scanning"**

#### Step 1: Add Environment Variables
Add this to the `environment` block in your Jenkinsfile:

```groovy
environment {{
    CODELOGIC_HOST = '{server_host}'
    AGENT_UUID = credentials('codelogic-agent-uuid')
    AGENT_PASSWORD = credentials('codelogic-agent-password')
}}
```

#### Step 2: Add CodeLogic Scan Stage
Insert this stage after your build stages:

```groovy
stage('CodeLogic Scan') {{
    when {{
        anyOf {{
            branch 'main'
            branch 'develop'
            branch 'feature/*'
        }}
    }}
    steps {{
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {{
            sh '''
                docker run --pull always --rm --interactive \\
                    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                    --env AGENT_UUID="${{AGENT_UUID}}" \\
                    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                    --volume "${{WORKSPACE}}:/scan" \\
                    ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest analyze \\
                    --application "{application_name}" \\
                    --path /scan \\
                    --scan-space-name "{scan_space_name}" \\
                    --rescan \\
                    --expunge-scan-sessions
            '''
        }}
    }}
}}
```

#### Step 3: Add Build Info Stage (Optional)
Add this stage for build information collection:

```groovy
stage('Send Build Info') {{
    when {{
        anyOf {{
            branch 'main'
            branch 'develop'
        }}
    }}
    steps {{
        sh '''
            docker run --rm \\
                --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                --env AGENT_UUID="${{AGENT_UUID}}" \\
                --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                --volume "${{WORKSPACE}}:/scan" \\
                --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest send_build_info \\
                --log-file="/log_file_path/build.log"
        '''
    }}
}}
```

#### Step 4: Add Post-Build Actions
Add this to the `post` block:

```groovy
post {{
    always {{
        archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true
    }}
}}
```

### 🔧 Jenkins Setup Instructions

**AI Prompt: "Set up Jenkins credentials for CodeLogic"**

1. **Add Credentials**:
   - Go to Jenkins → Manage Jenkins → Manage Credentials
   - Add Secret Text credentials:
     - ID: `codelogic-agent-uuid`
     - Secret: Your CodeLogic agent UUID
   - Add another Secret Text credential:
     - ID: `codelogic-agent-password` 
     - Secret: Your CodeLogic agent password

2. **Install Required Plugins**:
   - Docker Pipeline Plugin
   - Credentials Plugin

### 📋 Complete Jenkinsfile Template

**AI Prompt: "Create a complete Jenkinsfile with CodeLogic integration"**

```groovy
pipeline {{
    agent any
    
    environment {{
        CODELOGIC_HOST = '{server_host}'
        AGENT_UUID = credentials('codelogic-agent-uuid')
        AGENT_PASSWORD = credentials('codelogic-agent-password')
    }}
    
    stages {{
        stage('Build') {{
            steps {{
                // Your existing build steps
                echo 'Building application...'
            }}
        }}
        
        stage('Test') {{
            steps {{
                // Your existing test steps
                echo 'Running tests...'
            }}
        }}
        
        stage('CodeLogic Scan') {{
            when {{
                anyOf {{
                    branch 'main'
                    branch 'develop'
                    branch 'feature/*'
                }}
            }}
            steps {{
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {{
                    sh '''
                        docker run --pull always --rm --interactive \\
                            --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                            --env AGENT_UUID="${{AGENT_UUID}}" \\
                            --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                            --volume "${{WORKSPACE}}:/scan" \\
                            ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest analyze \\
                            --application "{application_name}" \\
                            --path /scan \\
                            --scan-space-name "{scan_space_name}" \\
                            --rescan \\
                            --expunge-scan-sessions
                    '''
                }}
            }}
        }}
        
        stage('Send Build Info') {{
            when {{
                anyOf {{
                    branch 'main'
                    branch 'develop'
                }}
            }}
            steps {{
                sh '''
                    docker run --rm \\
                        --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                        --env AGENT_UUID="${{AGENT_UUID}}" \\
                        --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                        --volume "${{WORKSPACE}}:/scan" \\
                        --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                        ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest send_build_info \\
                        --log-file="/log_file_path/build.log"
                '''
            }}
        }}
    }}
    
    post {{
        always {{
            archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true
        }}
        success {{
            echo 'Pipeline completed successfully'
        }}
        failure {{
            echo 'Pipeline failed'
        }}
    }}
}}
```
"""


def generate_github_actions_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host):
    """Generate GitHub Actions configuration with AI modification prompts"""
    return f"""
### 🎯 GitHub Actions File Modification Guide

**AI Prompt: "Modify GitHub Actions workflow to add CodeLogic scanning"**

#### Step 1: Add Secrets to Repository
**AI Prompt: "Add CodeLogic secrets to GitHub repository"**

1. Go to repository Settings → Secrets and variables → Actions
2. Add these repository secrets:
   - `CODELOGIC_HOST`: {server_host}
   - `AGENT_UUID`: Your CodeLogic agent UUID
   - `AGENT_PASSWORD`: Your CodeLogic agent password

#### Step 2: Create or Modify Workflow File
**AI Prompt: "Create .github/workflows/codelogic-scan.yml with CodeLogic integration"**

Create `.github/workflows/codelogic-scan.yml`:

```yaml
name: CodeLogic Scan

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main ]

jobs:
  codelogic-scan:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full git history for better analysis
      
    - name: CodeLogic Scan
      run: |
        docker run --pull always --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest analyze \\
          --application "{application_name}" \\
          --path /scan \\
          --scan-space-name "{scan_space_name}" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
      
    - name: Send Build Info
      if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
      run: |
        docker run --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log"
      continue-on-error: true
      
    - name: Upload build logs
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: build-logs
        path: logs/
        retention-days: 30
```

#### Step 3: Modify Existing Workflow
**AI Prompt: "Add CodeLogic scanning to existing GitHub Actions workflow"**

If you have an existing workflow, add these steps:

```yaml
# Add to your existing workflow
- name: CodeLogic Scan
  run: |
    docker run --pull always --rm \\
      --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
      --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
      --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
      --volume "${{{{ github.workspace }}}}:/scan" \\
      ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest analyze \\
      --application "{application_name}" \\
      --path /scan \\
      --scan-space-name "{scan_space_name}" \\
      --rescan \\
      --expunge-scan-sessions
  continue-on-error: true
```

### 🔧 GitHub Actions Setup Instructions

**AI Prompt: "Set up GitHub Actions for CodeLogic integration"**

1. **Repository Secrets**:
   - Go to repository Settings → Secrets and variables → Actions
   - Add repository secrets (not environment secrets)
   - Mark as sensitive data

2. **Workflow Permissions**:
   - Ensure workflow has necessary permissions
   - Add `permissions: contents: read` if needed

3. **Docker Support**:
   - GitHub Actions runners include Docker by default
   - No additional setup required

### 📋 Complete Workflow Template

**AI Prompt: "Create a complete GitHub Actions workflow with CodeLogic integration"**

```yaml
name: CI/CD Pipeline with CodeLogic

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: '6.0'
        
    - name: Restore dependencies
      run: dotnet restore
      
    - name: Build
      run: dotnet build --no-restore
      
    - name: Test
      run: dotnet test --no-build --verbosity normal
      
    - name: CodeLogic Scan
      run: |
        docker run --pull always --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest analyze \\
          --application "{application_name}" \\
          --path /scan \\
          --scan-space-name "{scan_space_name}" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
      
    - name: Send Build Info
      if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
      run: |
        docker run --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log"
      continue-on-error: true
      
    - name: Upload build logs
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: build-logs
        path: logs/
        retention-days: 30
```
"""


def generate_azure_devops_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host):
    """Generate Azure DevOps configuration"""
    return f"""
### Azure DevOps Pipeline

Create `azure-pipelines.yml`:

```yaml
trigger:
- main
- develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  codelogicHost: '{server_host}'
  agentUuid: $(codelogicAgentUuid)
  agentPassword: $(codelogicAgentPassword)

stages:
- stage: CodeLogicScan
  displayName: 'CodeLogic Scan'
  jobs:
  - job: Scan
    displayName: 'Run CodeLogic Scan'
    steps:
    - task: Docker@2
      displayName: 'CodeLogic Scan'
      inputs:
        command: 'run'
        arguments: |
          --pull always --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          $(codelogicHost)/codelogic_{agent_type}:latest analyze \\
          --application "{application_name}" \\
          --path /scan \\
          --scan-space-name "{scan_space_name}" \\
          --rescan \\
          --expunge-scan-sessions
      continueOnError: true
      
    - task: Docker@2
      displayName: 'Send Build Info'
      condition: and(succeededOrFailed(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
      inputs:
        command: 'run'
        arguments: |
          --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          --volume "$(Build.SourcesDirectory)/logs:/log_file_path" \\
          $(codelogicHost)/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log"
```

### Azure DevOps Variables

Add these variables to your pipeline:
- `codelogicAgentUuid`: Your agent UUID (mark as secret)
- `codelogicAgentPassword`: Your agent password (mark as secret)
"""


def generate_gitlab_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host):
    """Generate GitLab CI configuration"""
    return f"""
### GitLab CI Configuration

Create `.gitlab-ci.yml`:

```yaml
stages:
  - scan
  - build-info

variables:
  CODELOGIC_HOST: "{server_host}"
  DOCKER_DRIVER: overlay2

codelogic_scan:
  stage: scan
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker info
  script:
    - |
      docker run --pull always --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest analyze \\
        --application "{application_name}" \\
        --path /scan \\
        --scan-space-name "{scan_space_name}" \\
        --rescan \\
        --expunge-scan-sessions
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"
    - if: $CI_COMMIT_BRANCH =~ /^feature\\/.*$/
  allow_failure: true

send_build_info:
  stage: build-info
  image: docker:latest
  services:
    - docker:dind
  script:
    - |
      docker run --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        --volume "$CI_PROJECT_DIR/logs:/log_file_path" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest send_build_info \\
        --log-file="/log_file_path/build.log"
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"
  allow_failure: true
```

### GitLab Variables

Add these variables to your project:
- `AGENT_UUID`: Your agent UUID (mark as protected and masked)
- `AGENT_PASSWORD`: Your agent password (mark as protected and masked)
"""


def generate_generic_config(agent_type, scan_path, application_name, scan_space_name, include_build_info, server_host):
    """Generate generic configuration for any CI/CD platform"""
    return f"""
### Generic CI/CD Configuration

For any CI/CD platform, use these environment variables:

```bash
export CODELOGIC_HOST="{server_host}"
export AGENT_UUID="your-agent-uuid"
export AGENT_PASSWORD="your-agent-password"
```

### Shell Script Example

Create `codelogic-scan.sh`:

```bash
#!/bin/bash
set -e

# Configuration
CODELOGIC_HOST="${{CODELOGIC_HOST:-{server_host}}}"
AGENT_UUID="${{AGENT_UUID}}"
AGENT_PASSWORD="${{AGENT_PASSWORD}}"
SCAN_PATH="${{SCAN_PATH:-{scan_path}}}"
APPLICATION_NAME="${{APPLICATION_NAME:-{application_name}}}"
SCAN_SPACE="${{SCAN_SPACE:-{scan_space_name}}}"

# Run CodeLogic scan
echo "Starting CodeLogic {agent_type} scan..."
docker run --pull always --rm --interactive \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --volume "$SCAN_PATH:/scan" \\
    $CODELOGIC_HOST/codelogic_{agent_type}:latest analyze \\
    --application "$APPLICATION_NAME" \\
    --path /scan \\
    --scan-space-name "$SCAN_SPACE" \\
    --rescan \\
    --expunge-scan-sessions

echo "CodeLogic scan completed successfully"
"""


def generate_build_info_config(build_type, log_file_path, job_name, build_number, build_status, ci_platform, output_format):
    """Generate build information configuration with improved accuracy"""
    
    config = f"""# CodeLogic Build Information Configuration

## Build Type: {build_type.upper()}

**Important**: Build information is sent SEPARATELY from the main scan. This is for collecting build metadata, logs, and Git information to enhance CodeLogic analysis.

"""

    if build_type == "git-info":
        config += generate_git_info_config(output_format)
    elif build_type == "build-log":
        config += generate_build_log_config(log_file_path, output_format)
    elif build_type == "metadata":
        config += generate_metadata_config(job_name, build_number, build_status, ci_platform, output_format)
    else:  # all
        config += generate_all_build_info_config(log_file_path, job_name, build_number, build_status, ci_platform, output_format)

    return config


def generate_git_info_config(output_format):
    """Generate Git information configuration"""
    if output_format == "docker":
        return """
### Docker Command for Git Information

```bash
# Basic Git info collection
docker run --rm \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --volume "$PWD:/scan" \\
    your-codelogic-image send_build_info \\
    --log-file="/scan/build.log"
```

### Environment Variables for Git Context

```bash
export GIT_COMMIT=$(git rev-parse HEAD)
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export GIT_AUTHOR=$(git log -1 --pretty=format:'%an')
export GIT_MESSAGE=$(git log -1 --pretty=format:'%s')
```
"""
    else:
        return """
### Standalone Git Information Collection

```bash
#!/bin/bash
# Collect Git information
GIT_COMMIT=$(git rev-parse HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_AUTHOR=$(git log -1 --pretty=format:'%an')
GIT_MESSAGE=$(git log -1 --pretty=format:'%s')

# Send to CodeLogic
./send_build_info.sh \\
    --agent-uuid="$AGENT_UUID" \\
    --agent-password="$AGENT_PASSWORD" \\
    --server="$CODELOGIC_HOST" \\
    --log-file="build.log"
```
"""


def generate_build_log_config(log_file_path, output_format):
    """Generate build log configuration"""
    log_path = log_file_path or "/path/to/build.log"
    
    if output_format == "docker":
        return f"""
### Docker Command for Build Logs

```bash
# Mount log directory and send build logs
docker run --rm \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --volume "$PWD:/scan" \\
    --volume "/path/to/logs:/log_file_path" \\
    your-codelogic-image send_build_info \\
    --log-file="/log_file_path/{log_path.split('/')[-1]}"
```

### Log File Management

```bash
# Create log directory
mkdir -p logs

# Capture build output
your-build-command 2>&1 | tee logs/build.log

# Send to CodeLogic
docker run --rm \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --volume "$PWD:/scan" \\
    --volume "$PWD/logs:/log_file_path" \\
    your-codelogic-image send_build_info \\
    --log-file="/log_file_path/build.log"
```
"""
    else:
        return f"""
### Standalone Build Log Collection

```bash
#!/bin/bash
# Capture build logs
your-build-command 2>&1 | tee {log_path}

# Send to CodeLogic
./send_build_info.sh \\
    --agent-uuid="$AGENT_UUID" \\
    --agent-password="$AGENT_PASSWORD" \\
    --server="$CODELOGIC_HOST" \\
    --log-file="{log_path}"
```

### Advanced Log Management

```bash
# With log rotation and compression
./send_build_info.sh \\
    --agent-uuid="$AGENT_UUID" \\
    --agent-password="$AGENT_PASSWORD" \\
    --server="$CODELOGIC_HOST" \\
    --log-file="{log_path}" \\
    --log-lines=1000 \\
    --timeout=60
```
"""


def generate_metadata_config(job_name, build_number, build_status, ci_platform, output_format):
    """Generate metadata configuration"""
    job = job_name or "build-job"
    build_num = build_number or "123"
    status = build_status or "SUCCESS"
    platform = ci_platform or "jenkins"
    
    if output_format == "docker":
        return f"""
### Docker Command for Build Metadata

```bash
# Send build metadata
docker run --rm \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --volume "$PWD:/scan" \\
    your-codelogic-image send_build_info \\
    --log-file="/scan/build.log"
```

### CI/CD Platform Specific Metadata

#### Jenkins
```bash
export JOB_NAME="{job}"
export BUILD_NUMBER="{build_num}"
export BUILD_STATUS="{status}"
```

#### GitHub Actions
```bash
export GITHUB_REPOSITORY="${{{{ github.repository }}}}"
export GITHUB_SHA="${{{{ github.sha }}}}"
export GITHUB_REF="${{{{ github.ref }}}}"
```

#### Azure DevOps
```bash
export BUILD_BUILDID="${{{{ build.buildId }}}}"
export BUILD_DEFINITIONNAME="${{{{ build.definition.name }}}}"
export BUILD_REASON="${{{{ build.reason }}}}"
```
"""
    else:
        return f"""
### Standalone Metadata Collection

```bash
#!/bin/bash
# Set build metadata
export JOB_NAME="{job}"
export BUILD_NUMBER="{build_num}"
export BUILD_STATUS="{status}"
export CI_PLATFORM="{platform}"

# Send to CodeLogic
./send_build_info.sh \\
    --agent-uuid="$AGENT_UUID" \\
    --agent-password="$AGENT_PASSWORD" \\
    --server="$CODELOGIC_HOST" \\
    --log-file="build.log" \\
    --job-name="$JOB_NAME" \\
    --build-number="$BUILD_NUMBER"
```
"""


def generate_all_build_info_config(log_file_path, job_name, build_number, build_status, ci_platform, output_format):
    """Generate comprehensive build information configuration"""
    return f"""
# Complete CodeLogic Build Information Integration

## Comprehensive Setup

This configuration includes Git information, build logs, and metadata collection.

### Environment Setup

```bash
# CodeLogic Configuration
export CODELOGIC_HOST="https://your-instance.app.codelogic.com"
export AGENT_UUID="your-agent-uuid"
export AGENT_PASSWORD="your-agent-password"

# Build Information
export JOB_NAME="{job_name or 'build-job'}"
export BUILD_NUMBER="{build_number or '123'}"
export BUILD_STATUS="{build_status or 'SUCCESS'}"
export CI_PLATFORM="{ci_platform or 'jenkins'}"

# Git Information
export GIT_COMMIT=$(git rev-parse HEAD)
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export GIT_AUTHOR=$(git log -1 --pretty=format:'%an')
export GIT_MESSAGE=$(git log -1 --pretty=format:'%s')
```

### Complete Docker Command

```bash
# Full build information collection
docker run --rm \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --env JOB_NAME="$JOB_NAME" \\
    --env BUILD_NUMBER="$BUILD_NUMBER" \\
    --env BUILD_STATUS="$BUILD_STATUS" \\
    --env GIT_COMMIT="$GIT_COMMIT" \\
    --env GIT_BRANCH="$GIT_BRANCH" \\
    --volume "$PWD:/scan" \\
    --volume "$PWD/logs:/log_file_path" \\
    your-codelogic-image send_build_info \\
    --log-file="/log_file_path/{log_file_path or 'build.log'}" \\
    --job-name="$JOB_NAME" \\
    --build-number="$BUILD_NUMBER"
```

### CI/CD Platform Integration

#### Jenkins Pipeline
```groovy
pipeline {{
    environment {{
        CODELOGIC_HOST = 'https://your-instance.app.codelogic.com'
        AGENT_UUID = credentials('codelogic-agent-uuid')
        AGENT_PASSWORD = credentials('codelogic-agent-password')
    }}
    
    stages {{
        stage('Build') {{
            steps {{
                sh 'your-build-command 2>&1 | tee logs/build.log'
            }}
        }}
        
        stage('CodeLogic Build Info') {{
            steps {{
                sh '''
                    docker run --rm \\
                        --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                        --env AGENT_UUID="${{AGENT_UUID}}" \\
                        --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                        --volume "${{WORKSPACE}}:/scan" \\
                        --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                        ${{CODELOGIC_HOST}}/codelogic_dotnet:latest send_build_info \\
                        --log-file="/log_file_path/build.log" \\
                        --job-name="${{JOB_NAME}}" \\
                        --build-number="${{BUILD_NUMBER}}"
                '''
            }}
        }}
    }}
}}
```

### Best Practices

1. **Security**: Store credentials as environment variables or CI/CD secrets
2. **Logging**: Always capture build logs for comprehensive analysis
3. **Metadata**: Include job names, build numbers, and status information
4. **Git Context**: Capture commit hashes, branches, and author information
5. **Error Handling**: Use appropriate error handling for failed builds
6. **Performance**: Consider log file size limits for large builds
"""


def generate_pipeline_config(ci_platform, agent_type, scan_triggers, include_notifications, scan_space_strategy):
    """Generate complete pipeline configuration"""
    
    config = f"""# Complete CodeLogic CI/CD Pipeline Configuration

## Pipeline Overview

- **CI Platform**: {ci_platform.upper()}
- **Agent Type**: {agent_type.upper()}
- **Scan Triggers**: {', '.join(scan_triggers)}
- **Scan Space Strategy**: {scan_space_strategy}
- **Notifications**: {'Enabled' if include_notifications else 'Disabled'}

"""

    if ci_platform == "jenkins":
        config += generate_jenkins_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy)
    elif ci_platform == "github-actions":
        config += generate_github_actions_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy)
    elif ci_platform == "azure-devops":
        config += generate_azure_devops_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy)
    elif ci_platform == "gitlab":
        config += generate_gitlab_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy)
    
    config += f"""

## DevOps Best Practices

### Scan Space Management

Based on your strategy: **{scan_space_strategy}**

"""
    
    if scan_space_strategy == "unique-per-branch":
        config += """
- Each branch gets its own scan space
- Prevents conflicts between different development streams
- Recommended for feature branch workflows
- Use pattern: `{branch-name}-{timestamp}`
"""
    elif scan_space_strategy == "shared-development":
        config += """
- All development branches share the same scan space
- Simpler management but potential conflicts
- Good for small teams with coordinated development
- Use pattern: `Development-{team-name}`
"""
    else:  # environment-based
        config += """
- Scan spaces based on deployment environments
- Aligns with deployment pipeline stages
- Recommended for production workflows
- Use pattern: `{environment}-{application}`
"""

    config += f"""

### Security Configuration

```bash
# Environment Variables (store as secrets)
CODELOGIC_HOST="https://your-instance.app.codelogic.com"
AGENT_UUID="your-agent-uuid"
AGENT_PASSWORD="your-agent-password"

# Optional: Custom scan space naming
SCAN_SPACE_PREFIX="your-team"
```

### Error Handling Strategy

1. **Scan Failures**: Continue pipeline but mark as unstable
2. **Build Info Failures**: Log warnings but don't fail pipeline
3. **Network Issues**: Retry with exponential backoff
4. **Credential Issues**: Fail fast with clear error messages

### Performance Optimization

1. **Parallel Scanning**: Run multiple agent types simultaneously
2. **Incremental Scans**: Use `--rescan` for faster subsequent scans
3. **Resource Limits**: Set appropriate Docker memory limits
4. **Cache Management**: Use Docker layer caching for agent images

### Monitoring and Alerting

"""

    if include_notifications:
        config += """
- **Success Notifications**: Send to team channels on successful scans
- **Failure Alerts**: Immediate notification for scan failures
- **Trend Analysis**: Weekly reports on scan metrics
- **Integration**: Slack, Teams, or email notifications
"""
    else:
        config += """
- **Log-based Monitoring**: Use CI/CD platform logs for monitoring
- **Manual Review**: Regular review of scan results
- **Dashboard Integration**: Connect to monitoring dashboards
"""

    return config


def generate_jenkins_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy):
    """Generate complete Jenkins pipeline"""
    trigger_conditions = " || ".join([f"branch '{trigger}'" for trigger in scan_triggers])
    
    return f"""
### Complete Jenkins Pipeline

```groovy
pipeline {{
    agent any
    
    environment {{
        CODELOGIC_HOST = 'https://your-instance.app.codelogic.com'
        AGENT_UUID = credentials('codelogic-agent-uuid')
        AGENT_PASSWORD = credentials('codelogic-agent-password')
        SCAN_SPACE_STRATEGY = '{scan_space_strategy}'
    }}
    
    parameters {{
        choice(
            name: 'SCAN_SPACE_NAME',
            choices: ['Development', 'Staging', 'Production'],
            description: 'Target scan space for this run'
        )
        booleanParam(
            name: 'INCLUDE_BUILD_INFO',
            defaultValue: true,
            description: 'Include build information in scan'
        )
    }}
    
    stages {{
        stage('Prepare') {{
            steps {{
                script {{
                    // Determine scan space based on strategy
                    if (env.SCAN_SPACE_STRATEGY == 'unique-per-branch') {{
                        env.SCAN_SPACE = "${{env.BRANCH_NAME}}-${{env.BUILD_NUMBER}}"
                    }} else if (env.SCAN_SPACE_STRATEGY == 'environment-based') {{
                        env.SCAN_SPACE = "${{params.SCAN_SPACE_NAME}}-${{env.BRANCH_NAME}}"
                    }} else {{
                        env.SCAN_SPACE = params.SCAN_SPACE_NAME
                    }}
                }}
                echo "Using scan space: ${{env.SCAN_SPACE}}"
            }}
        }}
        
        stage('CodeLogic Scan') {{
            when {{
                anyOf {{
                    {trigger_conditions}
                }}
            }}
            steps {{
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {{
                    sh '''
                        echo "Starting CodeLogic {agent_type} scan..."
                        docker run --pull always --rm --interactive \\
                            --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                            --env AGENT_UUID="${{AGENT_UUID}}" \\
                            --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                            --volume "${{WORKSPACE}}:/scan" \\
                            ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest analyze \\
                            --application "${{JOB_NAME}}" \\
                            --path /scan \\
                            --scan-space-name "${{SCAN_SPACE}}" \\
                            --rescan \\
                            --expunge-scan-sessions
                    '''
                }}
            }}
        }}
        
        stage('Send Build Info') {{
            when {{
                anyOf {{
                    branch 'main'
                    branch 'develop'
                }}
                expression {{ params.INCLUDE_BUILD_INFO == true }}
            }}
            steps {{
                sh '''
                    echo "Sending build information to CodeLogic..."
                    docker run --rm \\
                        --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                        --env AGENT_UUID="${{AGENT_UUID}}" \\
                        --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                        --volume "${{WORKSPACE}}:/scan" \\
                        --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                        ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest send_build_info \\
                        --log-file="/log_file_path/build.log" \\
                        --job-name="${{JOB_NAME}}" \\
                        --build-number="${{BUILD_NUMBER}}"
                '''
            }}
        }}
    }}
    
    post {{
        always {{
            archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'logs',
                reportFiles: 'build.log',
                reportName: 'Build Logs'
            ])
        }}
        success {{
            echo "CodeLogic scan completed successfully"
        }}
        failure {{
            echo "CodeLogic scan failed - check logs for details"
        }}
    }}
}}
```

### Jenkins Configuration Steps

1. **Install Required Plugins**:
   - Docker Pipeline Plugin
   - HTML Publisher Plugin
   - Credentials Plugin

2. **Configure Credentials**:
   - Go to Manage Jenkins → Manage Credentials
   - Add Secret Text credentials:
     - ID: `codelogic-agent-uuid`
     - ID: `codelogic-agent-password`

3. **Configure Docker**:
   - Ensure Docker is available on Jenkins agents
   - Configure Docker daemon access for Jenkins user

4. **Set up Notifications** (if enabled):
   - Configure Slack/Teams integration
   - Set up email notifications for failures
"""


def generate_github_actions_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy):
    """Generate complete GitHub Actions pipeline"""
    return f"""
### Complete GitHub Actions Workflow

Create `.github/workflows/codelogic-pipeline.yml`:

```yaml
name: CodeLogic CI/CD Pipeline

on:
  push:
    branches: {scan_triggers}
  pull_request:
    branches: [ main, develop ]

env:
  CODELOGIC_HOST: ${{{{ secrets.CODELOGIC_HOST }}}}
  AGENT_UUID: ${{{{ secrets.AGENT_UUID }}}}
  AGENT_PASSWORD: ${{{{ secrets.AGENT_PASSWORD }}}}
  SCAN_SPACE_STRATEGY: {scan_space_strategy}

jobs:
  codelogic-scan:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        agent-type: [{agent_type}]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full git history for better analysis
    
    - name: Determine scan space
      id: scan-space
      run: |
        if [ "${{{{ env.SCAN_SPACE_STRATEGY }}}}" = "unique-per-branch" ]; then
          echo "space=${{{{ github.ref_name }}}}-${{{{ github.run_number }}}}" >> $GITHUB_OUTPUT
        elif [ "${{{{ env.SCAN_SPACE_STRATEGY }}}}" = "environment-based" ]; then
          echo "space=Development-${{{{ github.ref_name }}}}" >> $GITHUB_OUTPUT
        else
          echo "space=Development" >> $GITHUB_OUTPUT
        fi
    
    - name: CodeLogic Scan
      run: |
        echo "Starting CodeLogic ${{{{ matrix.agent-type }}}} scan..."
        docker run --pull always --rm \\
          --env CODELOGIC_HOST="${{{{ env.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ env.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ env.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          ${{{{ env.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest analyze \\
          --application "${{{{ github.repository }}}}" \\
          --path /scan \\
          --scan-space-name "${{{{ steps.scan-space.outputs.space }}}}" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
    
    - name: Send Build Info
      if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
      run: |
        echo "Sending build information to CodeLogic..."
        docker run --rm \\
          --env CODELOGIC_HOST="${{{{ env.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ env.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ env.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ env.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log" \\
          --job-name="${{{{ github.repository }}}}" \\
          --build-number="${{{{ github.run_number }}}}"
      continue-on-error: true
    
    - name: Upload build logs
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: build-logs
        path: logs/
        retention-days: 30

  notify:
    needs: codelogic-scan
    runs-on: ubuntu-latest
    if: always()
    steps:
    - name: Notify Success
      if: needs.codelogic-scan.result == 'success'
      run: |
        echo "CodeLogic scan completed successfully"
        # Add notification logic here
    
    - name: Notify Failure
      if: needs.codelogic-scan.result == 'failure'
      run: |
        echo "CodeLogic scan failed"
        # Add notification logic here
```

### GitHub Secrets Configuration

Add these secrets to your repository settings:

1. Go to Settings → Secrets and variables → Actions
2. Add the following repository secrets:
   - `CODELOGIC_HOST`: Your CodeLogic server URL
   - `AGENT_UUID`: Your agent UUID
   - `AGENT_PASSWORD`: Your agent password

### GitHub Actions Best Practices

1. **Security**: Use repository secrets for sensitive information
2. **Performance**: Use matrix strategy for multiple agent types
3. **Artifacts**: Upload build logs for debugging
4. **Notifications**: Integrate with Slack/Teams for status updates
5. **Caching**: Use Docker layer caching for faster builds
"""


def generate_azure_devops_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy):
    """Generate complete Azure DevOps pipeline"""
    return f"""
### Complete Azure DevOps Pipeline

Create `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include: {scan_triggers}

variables:
  codelogicHost: 'https://your-instance.app.codelogic.com'
  agentUuid: $(codelogicAgentUuid)
  agentPassword: $(codelogicAgentPassword)
  scanSpaceStrategy: {scan_space_strategy}

stages:
- stage: CodeLogicScan
  displayName: 'CodeLogic Scan'
  jobs:
  - job: Scan
    displayName: 'Run CodeLogic Scan'
    pool:
      vmImage: 'ubuntu-latest'
    
    steps:
    - task: Docker@2
      displayName: 'CodeLogic Scan'
      inputs:
        command: 'run'
        arguments: |
          --pull always --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          $(codelogicHost)/codelogic_{agent_type}:latest analyze \\
          --application "$(Build.DefinitionName)" \\
          --path /scan \\
          --scan-space-name "$(Build.BuildNumber)" \\
          --rescan \\
          --expunge-scan-sessions
      continueOnError: true
      
    - task: Docker@2
      displayName: 'Send Build Info'
      condition: and(succeededOrFailed(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
      inputs:
        command: 'run'
        arguments: |
          --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          --volume "$(Build.SourcesDirectory)/logs:/log_file_path" \\
          $(codelogicHost)/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log" \\
          --job-name="$(Build.DefinitionName)" \\
          --build-number="$(Build.BuildNumber)"
      continueOnError: true
      
    - task: PublishBuildArtifacts@1
      displayName: 'Publish Build Logs'
      inputs:
        pathToPublish: 'logs'
        artifactName: 'build-logs'
      condition: always()
```

### Azure DevOps Configuration

1. **Variable Groups**:
   - Create a variable group for CodeLogic configuration
   - Add variables: `codelogicAgentUuid`, `codelogicAgentPassword`
   - Mark as secret variables

2. **Service Connections**:
   - Configure Docker registry connections if needed
   - Set up authentication for private registries

3. **Notifications**:
   - Configure email notifications for build failures
   - Set up Slack/Teams integration for status updates
"""


def generate_gitlab_pipeline(agent_type, scan_triggers, include_notifications, scan_space_strategy):
    """Generate complete GitLab CI pipeline"""
    return f"""
### Complete GitLab CI Pipeline

Create `.gitlab-ci.yml`:

```yaml
variables:
  CODELOGIC_HOST: "https://your-instance.app.codelogic.com"
  AGENT_UUID: $AGENT_UUID
  AGENT_PASSWORD: $AGENT_PASSWORD
  SCAN_SPACE_STRATEGY: {scan_space_strategy}
  DOCKER_DRIVER: overlay2

stages:
  - scan
  - build-info
  - notify

codelogic_scan:
  stage: scan
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker info
    - |
      if [ "$SCAN_SPACE_STRATEGY" = "unique-per-branch" ]; then
        export SCAN_SPACE="$CI_COMMIT_REF_SLUG-$CI_PIPELINE_ID"
      elif [ "$SCAN_SPACE_STRATEGY" = "environment-based" ]; then
        export SCAN_SPACE="Development-$CI_COMMIT_REF_SLUG"
      else
        export SCAN_SPACE="Development"
      fi
  script:
    - |
      echo "Starting CodeLogic {agent_type} scan..."
      docker run --pull always --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest analyze \\
        --application "$CI_PROJECT_NAME" \\
        --path /scan \\
        --scan-space-name "$SCAN_SPACE" \\
        --rescan \\
        --expunge-scan-sessions
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^({scan_triggers.join('|')})$/
  allow_failure: true
  artifacts:
    reports:
      junit: logs/scan-results.xml
    paths:
      - logs/
    expire_in: 30 days

send_build_info:
  stage: build-info
  image: docker:latest
  services:
    - docker:dind
  script:
    - |
      echo "Sending build information to CodeLogic..."
      docker run --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        --volume "$CI_PROJECT_DIR/logs:/log_file_path" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest send_build_info \\
        --log-file="/log_file_path/build.log" \\
        --job-name="$CI_PROJECT_NAME" \\
        --build-number="$CI_PIPELINE_ID"
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"
  allow_failure: true

notify_success:
  stage: notify
  image: alpine:latest
  script:
    - echo "CodeLogic scan completed successfully"
    # Add notification logic here
  rules:
    - if: $CI_COMMIT_BRANCH == "main" && $codelogic_scan.status == "success"
  when: on_success

notify_failure:
  stage: notify
  image: alpine:latest
  script:
    - echo "CodeLogic scan failed"
    # Add notification logic here
  rules:
    - if: $CI_COMMIT_BRANCH == "main" && $codelogic_scan.status == "failed"
  when: on_failure
```

### GitLab CI Configuration

1. **Variables**:
   - Go to Settings → CI/CD → Variables
   - Add variables: `AGENT_UUID`, `AGENT_PASSWORD`
   - Mark as protected and masked

2. **Docker Configuration**:
   - Ensure Docker-in-Docker is enabled
   - Configure appropriate resource limits

3. **Notifications**:
   - Configure Slack/Teams integration
   - Set up email notifications for failures
"""
