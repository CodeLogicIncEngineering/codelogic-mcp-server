# CodeLogic MCP Server - Cursor Instructions

## About This Codebase

This repository contains a Model Context Protocol (MCP) server that integrates with CodeLogic's knowledge graph APIs. It enables AI programming assistants to access dependency data from CodeLogic to analyze code and database impacts.

## Key Technologies

- **Python 3.13+** with extensive use of async/await
- **Model Context Protocol SDK** (`mcp[cli]`)
- **Neo4j** for graph database operations
- **HTTPX** for API requests
- **Environment variables** via dotenv for configuration

## Project Structure

- **src/codelogic_mcp_server/**: Core package
- **`__init__.py`**: Package initialization and entry point  
- **`server.py`**: MCP server implementation  
- **`handlers.py`**: Tool handlers implementation  
- **`utils.py`**: API interaction utilities  

## Core Coding Patterns

### MCP Server Pattern

```python
server = Server("codelogic-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    # Define and return tools
    
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    # Handle tool execution
```

### Error Handling

```python
try:
    # Operations that might fail
except Exception as e:
    sys.stderr.write(f"Error: {str(e)}\n")
    return [types.TextContent(type="text", text=f"# Error\n\n{str(e)}")]
```

## Style Guidelines

1. **Copyright Headers**: Include MPL 2.0 headers in all Python files
2. **Docstrings**: Google-style docstrings for modules/classes/functions
3. **Type Hints**: Always use Python type hints
4. **Asynchronous**: Keep I/O operations asynchronous
5. **Format Outputs**: Return markdown-formatted text in tool responses

## Tool Implementation Pattern

When implementing new MCP tools:

1. Add to `handle_list_tools()` with descriptive name (prefix: `codelogic-`)
2. Add handler in `handle_call_tool()`
3. Implement handler function with error handling
4. Return results as markdown-formatted text

## Testing Approach

- **Unit Tests**: For functions without external dependencies
- **Integration Tests**: For tests against a real CodeLogic server
- Use the `CODELOGIC_TEST_MODE` environment variable

## Debugging

- Debug Mode: Set `CODELOGIC_DEBUG_MODE=true`
- Remote Debugging: Use debugpy capabilities

## Key Environment Variables

- `CODELOGIC_SERVER_HOST`: CodeLogic server URL
- `CODELOGIC_USERNAME`: Username for authentication
- `CODELOGIC_PASSWORD`: Password for authentication
- `CODELOGIC_MV_NAME`: Materialized view name
- `CODELOGIC_DEBUG_MODE`: Enable debug logging
- `CODELOGIC_TEST_MODE`: Used by test framework

## Cursor-Specific Features

### Code Analysis
- Use semantic search for finding relevant code snippets
- Utilize grep search for exact pattern matching
- Analyze method impacts before making changes
- Check database impacts for SQL and code changes

### File Operations
- Direct file editing with context preservation
- File creation and deletion capabilities
- Directory listing and navigation

### Terminal Integration
- Execute commands in the integrated terminal
- Background process management
- Environment variable handling

### Best Practices
1. Always check method impacts before making changes
2. Verify database impacts for SQL modifications
3. Use semantic search before grep for broader context
4. Maintain proper error handling and logging
5. Keep code changes atomic and focused

### Tool Usage Guidelines
1. **Code Search**: Use semantic search for understanding context
2. **File Operations**: Use edit_file for precise changes
3. **Terminal Commands**: Use run_terminal_cmd for shell operations
4. **Impact Analysis**: Use codelogic-method-impact and codelogic-database-impact before changes
5. **File Management**: Use list_dir and delete_file for file operations 