# codelogic-mcp-server

An [MCP Server](https://modelcontextprotocol.io/introduction) to utilize Codelogic's rich software dependency data in your AI programming assistant.

## Components

### Tools

The server implements two tools:

- **codelogic-method-impact**: Pulls an impact assessment from the CodeLogic server's APIs for your code.
  - Takes the given "method" that you're working on and its associated "class".
- **codelogic-database-impact**: Analyzes impacts between code and database entities.
  - Takes the database entity type (column, table, or view) and its name.

### Install

#### Pre Requisites

The MCP server relies upon Astral UV to run, please [install](https://docs.astral.sh/uv/getting-started/installation/)

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`
On Linux: `~/.config/Claude/claude_desktop_config.json`

```json
"mcpServers": {
  "codelogic-mcp-server": {
    "command": "uvx",
    "args": [
      "codelogic-mcp-server@latest"
    ],
    "env": {
      "CODELOGIC_SERVER_HOST": "<url to the server e.g. https://myco.app.codelogic.com>",
      "CODELOGIC_USERNAME": "<my username>",
      "CODELOGIC_PASSWORD": "<my password>",
      "CODELOGIC_MV_NAME": "<my marterialized view>"
    }
  }
}
```

#### Windsurf IDE

To run this MCP server with [Windsurf IDE](https://codeium.com/windsurf):

**Configure Windsurf IDE**:

To configure Windsurf IDE, you need to create or modify the `~/.codeium/windsurf/mcp_config.json` configuration file.

Add the following configuration to your file:

```json
"mcpServers": {
  "codelogic-mcp-server": {
    "command": "uvx",
    "args": [
      "codelogic-mcp-server@latest"
    ],
    "env": {
      "CODELOGIC_SERVER_HOST": "<url to the server e.g. https://myco.app.codelogic.com>",
      "CODELOGIC_USERNAME": "<my username>",
      "CODELOGIC_PASSWORD": "<my password>",
      "CODELOGIC_MV_NAME": "<my marterialized view>"
    }
  }
}
```

Add a **global rule** to help Windsurf call the tools, create or modify the `~/.codeium/windsurf/memories/global_rules.md` markdown file.

Add the following or something similar:

```markdown
When I ask you to modify existing code, try running the codelogic-method-impact and codelogic-database-impact MCP tools against the code I've provided and any methods or functions that you are changing. Make sure the results sent back from the tool are highlighted as impacts for the given method or function.
```

After adding the configuration, restart Windsurf IDE or refresh the tools to apply the changes.

### Environment Variables

The following environment variables can be configured to customize the behavior of the server:

- `CODELOGIC_SERVER_HOST`: The URL of the CodeLogic server.
- `CODELOGIC_USERNAME`: Your CodeLogic username.
- `CODELOGIC_PASSWORD`: Your CodeLogic password.
- `CODELOGIC_MV_NAME`: The name of the materialized view to use.
- `CODELOGIC_DEBUG_MODE`: Set to `true` to enable debug mode. When enabled, additional debug files such as `timing_log.txt` and `impact_data*.json` will be generated. Defaults to `false`.

#### Example Configuration

```json
"env": {
  "CODELOGIC_SERVER_HOST": "<url to the server e.g. https://myco.app.codelogic.com>",
  "CODELOGIC_USERNAME": "<my username>",
  "CODELOGIC_PASSWORD": "<my password>",
  "CODELOGIC_MV_NAME": "<my materialized view>",
  "CODELOGIC_DEBUG_MODE": "true"
}
```

#### Pinning the version

instead of using the **latest** version of the server, you can pin to a specific version by changing the **args** field to match the version in [pypi](https://pypi.org/project/codelogic-mcp-server/) e.g.

```json
    "args": [
      "codelogic-mcp-server@0.2.2"
    ],
```

## Testing

### Running Unit Tests

The project uses unittest for testing. You can run unit tests without any external dependencies:

```bash
python -m unittest discover -s test -p "unit_*.py"
```

Unit tests use mock data and don't require a connection to a CodeLogic server.

### Integration Tests (Optional)

If you want to run integration tests that connect to a real CodeLogic server:

1. Copy `test/.env.test.example` to `test/.env.test` and populate with your CodeLogic server details
2. Run the integration tests:

```bash
python -m unittest discover -s test -p "integration_*.py"
```

Note: Integration tests require access to a CodeLogic server instance.
