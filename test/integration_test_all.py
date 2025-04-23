import os
import sys
import asyncio
from dotenv import load_dotenv
import mcp.types as types
from test.test_fixtures import setup_test_environment
from test.test_env import TestCase

# Add the parent directory to Python path to make the absolute import work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def load_test_config(env_file=None):
    """Load environment configuration from .env file or environment variables."""
    # Get test directory path
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(test_dir, '..'))
    
    # First try to load from specified env file
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
    # Then try test-specific env file in the test directory
    elif os.path.exists(os.path.join(test_dir, '.env.test')):
        load_dotenv(os.path.join(test_dir, '.env.test'))
    # Next try project root .env file
    elif os.path.exists(os.path.join(project_root, '.env')):
        load_dotenv(os.path.join(project_root, '.env'))

    return {
        'CODELOGIC_WORKSPACE_NAME': os.getenv('CODELOGIC_WORKSPACE_NAME'),
        'CODELOGIC_SERVER_HOST': os.getenv('CODELOGIC_SERVER_HOST'),
        'CODELOGIC_USERNAME': os.getenv('CODELOGIC_USERNAME'),
        'CODELOGIC_PASSWORD': os.getenv('CODELOGIC_PASSWORD'),
    }


class TestHandleCallToolIntegration(TestCase):
    """Integration tests for handle_call_tool using clean test environment.

    To run these tests:
    1. Create a .env.test file with your credentials, or
    2. Set environment variables as specified in .env.example
    """

    @classmethod
    def setUpClass(cls):
        """Set up test configuration from environment variables"""
        cls.config = load_test_config()

    def run_impact_test(self, method_name, class_name, output_file):
        """Helper to run a parameterized impact analysis test"""
        # Skip test if credentials are not provided
        if not self.config.get('CODELOGIC_USERNAME') or not self.config.get('CODELOGIC_PASSWORD'):
            self.skipTest("Skipping integration test: No credentials provided in environment")

        # Setup environment with configuration
        handle_call_tool, *_ = setup_test_environment(self.config)

        async def run_test():
            result = await handle_call_tool('codelogic-method-impact', {'method': method_name, 'class': class_name})

            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)

            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(result[0].text)

            self.assertIn(f"# Impact Analysis for Method: `{method_name}`", result[0].text)
            return result

        return asyncio.run(run_test())

    def test_handle_call_tool_codelogic_method_impact_multi_app_java(self):
        """Test impact analysis on Java multi-app environment"""
        self.run_impact_test(
            'addPrefix',
            'CompanyInfo',
            'impact_analysis_result_multi_app_java.md'
        )

    def test_handle_call_tool_codelogic_method_impact_dotnet(self):
        """Test impact analysis on .NET environment"""
        self.run_impact_test(
            'IsValid',
            'AnalysisOptionsValidator',
            'impact_analysis_result_dotnet.md'
        )


class TestUtils(TestCase):
    """Test utility functions using the clean test environment."""

    @classmethod
    def setUpClass(cls):
        """Set up test resources that can be shared across test methods."""
        # Note: We're not calling super().setUpClass() because TestCase doesn't override it

        # Setup environment for integration tests
        handle_call_tool, get_mv_definition_id, get_mv_id_from_def, get_method_nodes, get_impact, authenticate = setup_test_environment({})

        # Initialize shared test resources
        cls.token = authenticate()
        cls.mv_name = os.getenv('CODELOGIC_WORKSPACE_NAME')
        cls.mv_def_id = get_mv_definition_id(cls.mv_name, cls.token)
        cls.mv_id = get_mv_id_from_def(cls.mv_def_id, cls.token)
        cls.nodes = get_method_nodes(cls.mv_id, 'IsValid')
        cls.get_method_nodes = get_method_nodes
        cls.get_impact = get_impact

    def test_authenticate(self):
        self.assertIsNotNone(self.token)

    def test_get_mv_definition_id(self):
        self.assertRegex(self.mv_def_id, r'^[0-9a-fA-F-]{36}$')

    def test_get_mv_id_from_def(self):
        self.assertRegex(self.mv_id, r'^[0-9a-fA-F-]{36}$')

    def test_get_method_nodes(self):
        self.assertIsInstance(self.nodes, list)

    def test_get_impact(self):
        node_id = self.nodes[0]['id'] if self.nodes else None
        self.assertIsNotNone(node_id, "Node ID should not be None")
        impact = self.get_impact(node_id)
        self.assertIsInstance(impact, str)


if __name__ == '__main__':
    import unittest
    unittest.main()
