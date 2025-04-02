import os
import importlib

# Base test environment setup
os.environ['CODELOGIC_TEST_MODE'] = 'true'


def setup_test_environment(env_vars):
    """Set environment variables and reload affected modules"""
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value

    # Override CODELOGIC_SERVER_HOST for tests
    os.environ['CODELOGIC_SERVER_HOST'] = 'http://testserver'

    # Reload the utils module to ensure it picks up the updated environment variables
    import codelogic_mcp_server.utils
    importlib.reload(codelogic_mcp_server.utils)

    # Reinitialize the HTTP client in utils to use the updated environment variables
    codelogic_mcp_server.utils._client = codelogic_mcp_server.utils.httpx.Client(
        timeout=codelogic_mcp_server.utils.httpx.Timeout(
            codelogic_mcp_server.utils.REQUEST_TIMEOUT,
            connect=codelogic_mcp_server.utils.CONNECT_TIMEOUT
        ),
        limits=codelogic_mcp_server.utils.httpx.Limits(
            max_keepalive_connections=20,
            max_connections=30
        ),
        transport=codelogic_mcp_server.utils.httpx.HTTPTransport(retries=3)
    )

    # Only import handlers after environment is properly configured
    import codelogic_mcp_server.handlers
    importlib.reload(codelogic_mcp_server.handlers)

    # Return the imported modules for convenience
    from codelogic_mcp_server.handlers import handle_call_tool
    from codelogic_mcp_server.utils import (
        get_mv_definition_id,
        get_mv_id_from_def,
        get_method_nodes,
        get_impact,
        authenticate
    )

    return handle_call_tool, get_mv_definition_id, get_mv_id_from_def, get_method_nodes, get_impact, authenticate
