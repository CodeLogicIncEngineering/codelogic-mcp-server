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

<details>
<summary><h4>Visual Studio Code Configuration</h4></summary>

To configure this MCP server in VS Code:

1. First, ensure you have GitHub Copilot agent mode enabled in VS Code.

2. Create a `.vscode/mcp.json` file in your workspace with the following configuration:

```json
{
  "servers": {
    "codelogic-mcp-server": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "codelogic-mcp-server@latest"
      ],
      "env": {
        "CODELOGIC_SERVER_HOST": "<url to the server e.g. https://myco.app.codelogic.com>",
        "CODELOGIC_USERNAME": "<my username>",
        "CODELOGIC_PASSWORD": "<my password>",
        "CODELOGIC_MV_NAME": "<my materialized view>",
        "CODELOGIC_DEBUG_MODE": "true"
      }
    }
  }
}
```

3. Alternatively, you can run the `MCP: Add Server` command from the Command Palette and provide the server information.

4. To manage your MCP servers, use the `MCP: List Servers` command from the Command Palette.

5. Once configured, the server's tools will be available to Copilot agent mode. You can toggle specific tools on/off as needed by clicking the Tools button in the Chat view when in agent mode.

6. To use the Codelogic tools in agent mode, you can specifically ask about code impacts or database relationships, and the agent will utilize the appropriate tools.

</details>

<details>
<summary><h4>Claude Desktop Configuration</h4></summary>

Configure Claude Desktop by editing the configuration file:

- On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
- On Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- On Linux: `~/.config/Claude/claude_desktop_config.json`

Add the following to your configuration file:

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
      "CODELOGIC_MV_NAME": "<my materialized view>"
    }
  }
}
```

After adding the configuration, restart Claude Desktop to apply the changes.
</details>

<details>
<summary><h4>Windsurf IDE Configuration</h4></summary>

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
      "CODELOGIC_MV_NAME": "<my materialized view>"
    }
  }
}
```

After adding the configuration, restart Windsurf IDE or refresh the tools to apply the changes.
</details>

<details>
<summary><h4>Cursor Configuration</h4></summary>

To configure the CodeLogic MCP server in Cursor:

1. Configure the MCP server by creating a `.cursor/mcp.json` file:

```json
{
  "servers": {
    "codelogic-mcp-server": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "codelogic-mcp-server@latest"
      ],
      "env": {
        "CODELOGIC_SERVER_HOST": "<url to the server e.g. https://myco.app.codelogic.com>",
        "CODELOGIC_USERNAME": "<my username>",
        "CODELOGIC_PASSWORD": "<my password>",
        "CODELOGIC_MV_NAME": "<my materialized view>",
        "CODELOGIC_DEBUG_MODE": "true"
      }
    }
  }
}
```

2. Restart Cursor to apply the changes.

The CodeLogic MCP server tools will now be available in your Cursor workspace.
</details>

### AI Assistant Instructions

To help the AI assistant use the CodeLogic tools effectively, you can add the following instructions to your client's configuration:

<details>
<summary><h4>VS Code (GitHub Copilot) Instructions</h4></summary>

Create a `.vscode/copilot-instructions.md` file with the following content:

```markdown
# CodeLogic MCP Server Instructions

When modifying existing code methods:
- Use codelogic-method-impact to analyze code changes
- Use codelogic-database-impact for database modifications
- Highlight impact results for the modified methods

When modifying SQL code or database entities:
- Always use codelogic-database-impact to analyze potential impacts
- Highlight impact results for the modified database entities

To use the CodeLogic tools effectively:
- For code impacts: Ask about specific methods or functions
- For database relationships: Ask about tables, views, or columns
- Review the impact results before making changes
- Consider both direct and indirect impacts
```
</details>

<details>
<summary><h4>Claude Desktop Instructions</h4></summary>

Create a file `~/.claude/instructions.md` with the following content:

```markdown
# CodeLogic MCP Server Instructions

When modifying existing code methods:
- Use codelogic-method-impact to analyze code changes
- Use codelogic-database-impact for database modifications
- Highlight impact results for the modified methods

When modifying SQL code or database entities:
- Always use codelogic-database-impact to analyze potential impacts
- Highlight impact results for the modified database entities

To use the CodeLogic tools effectively:
- For code impacts: Ask about specific methods or functions
- For database relationships: Ask about tables, views, or columns
- Review the impact results before making changes
- Consider both direct and indirect impacts
```
</details>

<details>
<summary><h4>Windsurf IDE Instructions</h4></summary>

Create or modify the `~/.codeium/windsurf/memories/global_rules.md` markdown file with the following content:

```markdown
When modifying existing code methods:
- Use codelogic-method-impact to analyze code changes
- Use codelogic-database-impact for database modifications
- Highlight impact results for the modified methods

When modifying SQL code or database entities:
- Always use codelogic-database-impact to analyze potential impacts
- Highlight impact results for the modified database entities

To use the CodeLogic tools effectively:
- For code impacts: Ask about specific methods or functions
- For database relationships: Ask about tables, views, or columns
- Review the impact results before making changes
- Consider both direct and indirect impacts
```
</details>

<details>
<summary><h4>Cursor Instructions</h4></summary>

Create a `.cursor/rules/codelogic-rules.md` file with the following content:

```markdown
# CodeLogic MCP Server Rules

## AI Assistant Behavior
- When modifying existing code methods:
  - Use codelogic-method-impact to analyze code changes
  - Use codelogic-database-impact for database modifications
  - Highlight impact results for the modified methods
- When modifying SQL code or database entities:
  - Always use codelogic-database-impact to analyze potential impacts
  - Highlight impact results for the modified database entities
- To use the CodeLogic tools effectively:
  - For code impacts: Ask about specific methods or functions
  - For database relationships: Ask about tables, views, or columns
  - Review the impact results before making changes
  - Consider both direct and indirect impacts
```
</details>

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

#### Version Compatibility

This MCP server has the following version compatibility requirements:

- Version 0.3.1 and below: Compatible with all CodeLogic API versions
- Version 0.4.0 and above: Requires CodeLogic API version 25.10.0 or greater

If you're upgrading, make sure your CodeLogic server meets the minimum API version requirement.

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
