# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Unit tests for CI handler log filtering functionality.
"""

import asyncio
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

from test.test_env import TestCase

# Import after test_env sets up the environment
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from codelogic_mcp_server.handlers.ci import (
    analyze_build_logs,
    generate_log_filter_script,
    generate_log_filtering_instructions,
    handle_ci as _handle_ci_async,
)


def handle_ci(arguments):
    """Run async handle_ci from sync tests."""
    return asyncio.run(_handle_ci_async(arguments))


class TestAnalyzeBuildLogs(TestCase):
    """Test the analyze_build_logs function"""

    def test_analyze_build_logs_empty_input(self):
        """Test with no logs provided"""
        result = analyze_build_logs(None, None)
        self.assertEqual(result, {})

    def test_analyze_build_logs_successful_only(self):
        """Test with only successful log"""
        successful_log = """Building project...
Compiling...
Downloading dependencies...
Downloading dependencies...
Downloading dependencies...
Build succeeded!
"""
        result = analyze_build_logs(successful_log, None)
        
        self.assertIsInstance(result, dict)
        self.assertIn("patterns_to_filter", result)
        self.assertIn("exact_lines_to_filter", result)
        self.assertIn("short_lines_to_filter", result)
        self.assertIn("verbose_prefixes", result)
        self.assertIn("summary", result)
        
        # Should identify repetitive lines
        self.assertGreater(len(result["exact_lines_to_filter"]), 0)
        # "Downloading dependencies..." should be identified as repetitive
        self.assertIn("Downloading dependencies...", result["exact_lines_to_filter"])

    def test_analyze_build_logs_failed_only(self):
        """Test with only failed log"""
        failed_log = """Building project...
Compiling...
Error: Build failed
Error: Build failed
Error: Build failed
Test failed: assertion error
"""
        result = analyze_build_logs(None, failed_log)
        
        self.assertIsInstance(result, dict)
        self.assertIn("exact_lines_to_filter", result)
        # "Error: Build failed" should be identified as repetitive
        self.assertIn("Error: Build failed", result["exact_lines_to_filter"])

    def test_analyze_build_logs_both_logs(self):
        """Test with both successful and failed logs"""
        successful_log = """Building...
Installing package...
Installing package...
Installing package...
Build succeeded
"""
        failed_log = """Building...
Restoring packages...
Restoring packages...
Error occurred
"""
        result = analyze_build_logs(successful_log, failed_log)
        
        self.assertIsInstance(result, dict)
        self.assertGreater(result["summary"]["total_lines_analyzed"], 0)
        # Should identify patterns from both logs
        self.assertIn("Installing package...", result["exact_lines_to_filter"])
        self.assertIn("Restoring packages...", result["exact_lines_to_filter"])

    def test_analyze_build_logs_identifies_short_lines(self):
        """Test that very short lines are identified"""
        log = """OK
OK
OK
PASS
PASS
Building project...
"""
        result = analyze_build_logs(log, None)
        
        self.assertIsInstance(result, dict)
        self.assertIn("short_lines_to_filter", result)
        # Short repetitive lines should be identified
        self.assertGreater(len(result["short_lines_to_filter"]), 0)

    def test_analyze_build_logs_identifies_verbose_prefixes(self):
        """Test that verbose prefixes are identified"""
        log = """Downloading package1...
Downloading package2...
Downloading package3...
Installing component1...
Installing component2...
Building project...
"""
        result = analyze_build_logs(log, None)
        
        self.assertIsInstance(result, dict)
        self.assertIn("verbose_prefixes", result)
        # "Downloading" and "Installing" should be identified as verbose prefixes
        self.assertIn("Downloading", result["verbose_prefixes"])
        self.assertIn("Installing", result["verbose_prefixes"])

    def test_analyze_build_logs_empty_lines_filtered(self):
        """Test that empty lines are included in base patterns"""
        log = """Line 1

Line 2

Line 3
"""
        result = analyze_build_logs(log, None)
        
        self.assertIsInstance(result, dict)
        self.assertIn("patterns_to_filter", result)
        # Should include pattern for empty lines
        empty_line_pattern = r'^\s*$'
        self.assertIn(empty_line_pattern, result["patterns_to_filter"])

    def test_analyze_build_logs_summary_statistics(self):
        """Test that summary statistics are correct"""
        log = """Line 1
Line 2
Line 1
Line 2
Line 1
Unique line
"""
        result = analyze_build_logs(log, None)
        
        self.assertIn("summary", result)
        summary = result["summary"]
        self.assertIn("total_lines_analyzed", summary)
        self.assertIn("repetitive_lines_found", summary)
        self.assertIn("short_noise_lines_found", summary)
        self.assertIn("verbose_prefixes_found", summary)
        # Trailing newline in triple-quoted string yields 7 lines (last empty)
        self.assertEqual(summary["total_lines_analyzed"], 7)


class TestGenerateLogFilterScript(TestCase):
    """Test the generate_log_filter_script function"""

    def test_generate_log_filter_script_empty_config(self):
        """Test with empty filtering config"""
        result = generate_log_filter_script({}, "jenkins")
        self.assertEqual(result, "")

    def test_generate_log_filter_script_basic_config(self):
        """Test with basic filtering config"""
        config = {
            "patterns_to_filter": [r'^\s*$'],
            "exact_lines_to_filter": ["Repetitive line"],
            "short_lines_to_filter": ["OK"],
            "verbose_prefixes": ["Downloading"],
            "min_line_length": 5,
            "max_repetition": 3
        }
        result = generate_log_filter_script(config, "jenkins")
        
        self.assertIsInstance(result, str)
        self.assertIn("filter_log()", result)
        self.assertIn("input_file", result)
        self.assertIn("output_file", result)
        # Should include filtering logic
        self.assertIn("skip_line", result)

    def test_generate_log_filter_script_includes_patterns(self):
        """Test that patterns are included in the script"""
        config = {
            "patterns_to_filter": [r'^Downloading.*?$', r'^Installing.*?$'],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3
        }
        result = generate_log_filter_script(config, "jenkins")
        
        # Should include grep commands for patterns
        self.assertIn("grep -qE", result)

    def test_generate_log_filter_script_includes_exact_lines(self):
        """Test that exact lines are included in the script"""
        config = {
            "patterns_to_filter": [],
            "exact_lines_to_filter": ["Repetitive line 1", "Repetitive line 2"],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3
        }
        result = generate_log_filter_script(config, "jenkins")
        
        # Should include exact line matching
        self.assertIn("Repetitive line 1", result)
        self.assertIn("Repetitive line 2", result)

    def test_generate_log_filter_script_includes_short_lines(self):
        """Test that short lines are included in the script"""
        config = {
            "patterns_to_filter": [],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": ["OK", "PASS"],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3
        }
        result = generate_log_filter_script(config, "jenkins")
        
        # Should include short line matching
        self.assertIn("OK", result)
        self.assertIn("PASS", result)

    def test_generate_log_filter_script_includes_verbose_prefixes(self):
        """Test that verbose prefixes are included in the script"""
        config = {
            "patterns_to_filter": [],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": [],
            "verbose_prefixes": ["Downloading", "Installing"],
            "min_line_length": 3,
            "max_repetition": 5
        }
        result = generate_log_filter_script(config, "jenkins")
        
        # Should include prefix filtering logic
        self.assertIn("Downloading", result)
        self.assertIn("Installing", result)
        self.assertIn("prefix_count", result)

    def test_generate_log_filter_script_platform_agnostic(self):
        """Test that script works for different platforms"""
        config = {
            "patterns_to_filter": [r'^\s*$'],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3
        }
        
        for platform in ["jenkins", "github-actions", "azure-devops", "gitlab"]:
            result = generate_log_filter_script(config, platform)
            self.assertIsInstance(result, str)
            self.assertIn("filter_log()", result)


class TestGenerateLogFilteringInstructions(TestCase):
    """Test the generate_log_filtering_instructions function"""

    def test_generate_log_filtering_instructions_empty_config(self):
        """Test with empty config"""
        result = generate_log_filtering_instructions(None, "jenkins")
        self.assertEqual(result, "")

    def test_generate_log_filtering_instructions_jenkins(self):
        """Test instructions for Jenkins"""
        config = {
            "patterns_to_filter": [r'^\s*$'],
            "exact_lines_to_filter": ["Repetitive line"],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3,
            "summary": {
                "total_lines_analyzed": 100,
                "repetitive_lines_found": 5,
                "short_noise_lines_found": 10,
                "verbose_prefixes_found": 2
            }
        }
        result = generate_log_filtering_instructions(config, "jenkins", "dotnet")
        
        self.assertIsInstance(result, str)
        self.assertIn("Log Filtering Configuration", result)
        self.assertIn("Jenkins", result)
        self.assertIn("filterLog", result)
        self.assertIn("100", result)  # Total lines analyzed

    def test_generate_log_filtering_instructions_github_actions(self):
        """Test instructions for GitHub Actions"""
        config = {
            "patterns_to_filter": [r'^\s*$'],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3,
            "summary": {
                "total_lines_analyzed": 50,
                "repetitive_lines_found": 3,
                "short_noise_lines_found": 5,
                "verbose_prefixes_found": 1
            }
        }
        result = generate_log_filtering_instructions(config, "github-actions", "java")
        
        self.assertIsInstance(result, str)
        self.assertIn("GitHub Actions", result)
        self.assertIn("Filter build logs", result)

    def test_generate_log_filtering_instructions_azure_devops(self):
        """Test instructions for Azure DevOps"""
        config = {
            "patterns_to_filter": [],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3,
            "summary": {
                "total_lines_analyzed": 75,
                "repetitive_lines_found": 4,
                "short_noise_lines_found": 8,
                "verbose_prefixes_found": 3
            }
        }
        result = generate_log_filtering_instructions(config, "azure-devops", "javascript")
        
        self.assertIsInstance(result, str)
        self.assertIn("Azure DevOps", result)
        self.assertIn("Bash@3", result)

    def test_generate_log_filtering_instructions_gitlab(self):
        """Test instructions for GitLab"""
        config = {
            "patterns_to_filter": [],
            "exact_lines_to_filter": [],
            "short_lines_to_filter": [],
            "verbose_prefixes": [],
            "min_line_length": 3,
            "max_repetition": 3,
            "summary": {
                "total_lines_analyzed": 200,
                "repetitive_lines_found": 10,
                "short_noise_lines_found": 15,
                "verbose_prefixes_found": 5
            }
        }
        result = generate_log_filtering_instructions(config, "gitlab", "sql")
        
        self.assertIsInstance(result, str)
        self.assertIn("GitLab", result)
        self.assertIn("filter_logs", result)


class TestHandleCiWithLogFiltering(TestCase):
    """Test handle_ci function with log filtering"""

    @patch.dict(os.environ, {'CODELOGIC_SERVER_HOST': 'https://test.codelogic.com'})
    def test_handle_ci_without_logs(self):
        """Test handle_ci without log examples"""
        arguments = {
            "agent_type": "dotnet",
            "scan_path": "/path/to/scan",
            "application_name": "TestApp",
            "ci_platform": "jenkins"
        }
        
        result = handle_ci(arguments)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should not include log filtering section
        self.assertNotIn("Log Filtering Configuration", result[0].text)

    @patch.dict(os.environ, {'CODELOGIC_SERVER_HOST': 'https://test.codelogic.com'})
    def test_handle_ci_with_successful_log(self):
        """Test handle_ci with successful log example"""
        arguments = {
            "agent_type": "java",
            "scan_path": "/path/to/scan",
            "application_name": "TestApp",
            "ci_platform": "github-actions",
            "successful_build_log": """Building...
Installing...
Installing...
Build succeeded
"""
        }
        
        result = handle_ci(arguments)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should include log filtering section
        self.assertIn("Log Filtering Configuration", result[0].text)
        self.assertIn("Analysis Summary", result[0].text)

    @patch.dict(os.environ, {'CODELOGIC_SERVER_HOST': 'https://test.codelogic.com'})
    def test_handle_ci_with_failed_log(self):
        """Test handle_ci with failed log example"""
        arguments = {
            "agent_type": "javascript",
            "scan_path": "/path/to/scan",
            "application_name": "TestApp",
            "ci_platform": "azure-devops",
            "failed_build_log": """Building...
Error occurred
Error occurred
Build failed
"""
        }
        
        result = handle_ci(arguments)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should include log filtering section
        self.assertIn("Log Filtering Configuration", result[0].text)

    @patch.dict(os.environ, {'CODELOGIC_SERVER_HOST': 'https://test.codelogic.com'})
    def test_handle_ci_with_both_logs(self):
        """Test handle_ci with both successful and failed logs"""
        arguments = {
            "agent_type": "dotnet",
            "scan_path": "/path/to/scan",
            "application_name": "TestApp",
            "ci_platform": "gitlab",
            "successful_build_log": """Building...
Installing...
Build succeeded
""",
            "failed_build_log": """Building...
Error occurred
Build failed
"""
        }
        
        result = handle_ci(arguments)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should include log filtering section
        self.assertIn("Log Filtering Configuration", result[0].text)
        # Should analyze both logs
        self.assertIn("Total lines analyzed", result[0].text)


if __name__ == '__main__':
    unittest.main()
