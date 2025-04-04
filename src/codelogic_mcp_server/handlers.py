# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
MCP tool handlers for the CodeLogic server integration.

This module implements the handlers for MCP tool operations, specifically the
get-impact tool that analyzes the potential impact of modifying a method or function.
It processes requests, performs impact analysis using the CodeLogic API, and formats
results for display to users.
"""

import json
import os
import sys
from .server import server
import mcp.types as types
from .utils import extract_nodes, extract_relationships, get_mv_id, get_method_nodes, get_impact, find_node_by_id
import time
from datetime import datetime


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-impact",
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
    if name != "get-impact":
        sys.stderr.write(f"Unknown tool: {name}\n")
        raise ValueError(f"Unknown tool: {name}")

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

    mv_id = get_mv_id(os.getenv("CODELOGIC_MV_NAME"))

    start_time = time.time()
    nodes = get_method_nodes(mv_id, method_name)
    end_time = time.time()
    duration = end_time - start_time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("timing_log.txt", "a") as log_file:
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
    with open("timing_log.txt", "a") as log_file:
        log_file.write(f"{timestamp} - get_impact for node '{node['name']}' took {duration:.4f} seconds\n")
    with open("impact_data.json", "w") as impact_file:
        json.dump(impact, impact_file, indent=4)
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

    # Identify REST endpoints or API controllers that might be affected
    rest_endpoints = []
    api_controllers = []
    endpoint_nodes = []

    # Look for Endpoint nodes directly
    for node_item in nodes:
        # Check for Endpoint primary label
        if node_item.get('primaryLabel') == 'Endpoint':
            endpoint_nodes.append({
                'name': node_item.get('name', ''),
                'path': node_item.get('properties', {}).get('path', ''),
                'http_verb': node_item.get('properties', {}).get('httpVerb', ''),
                'id': node_item.get('id')
            })

        # Check for controller types
        if any(term in node_item.get('primaryLabel', '').lower() for term in
                ['controller', 'restendpoint', 'apiendpoint', 'webservice']):
            api_controllers.append({
                'name': node_item.get('name', ''),
                'type': node_item.get('primaryLabel', '')
            })

        # Check for REST annotations on methods
        if node_item.get('primaryLabel') in ['JavaMethodEntity', 'DotNetMethodEntity']:
            annotations = node_item.get('properties', {}).get('annotations', [])
            if annotations and any(
                    anno.lower() in str(annotations).lower() for anno in
                    [
                        'getmapping', 'postmapping', 'putmapping', 'deletemapping',
                        'requestmapping', 'httpget', 'httppost', 'httpput', 'httpdelete'
                    ]):
                rest_endpoints.append({
                    'name': node_item.get('name', ''),
                    'annotation': str([a for a in annotations if any(m in a.lower() for m in ['mapping', 'http'])])
                })

    # Look for endpoint-to-endpoint dependencies
    endpoint_dependencies = []
    for rel in impact_data.get('data', {}).get('relationships', []):
        if rel.get('type') in ['INVOKES_ENDPOINT', 'REFERENCES_ENDPOINT']:
            start_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel.get('startId'))
            end_node = find_node_by_id(impact_data.get('data', {}).get('nodes', []), rel.get('endId'))

            if start_node and end_node:
                endpoint_dependencies.append({
                    'source': start_node.get('name', 'Unknown'),
                    'target': end_node.get('name', 'Unknown')
                })

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
- **Complexity**: {complexity}
- **Instruction Count**: {instruction_count}
- **Affected Applications**: {len(affected_applications)}
"""

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
