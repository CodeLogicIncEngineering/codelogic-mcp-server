# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Common utilities and shared functions for CodeLogic MCP handlers.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
import time


DEBUG_MODE = os.getenv("CODELOGIC_DEBUG_MODE", "false").lower() == "true"

# Dedicated send-build-info image (not agent images). Agent images no longer include send_build_info.
SEND_BUILD_INFO_IMAGE = "public.ecr.aws/codelogic.com/codelogic_send-build-info:latest"
SEND_BUILD_INFO_GITHUB_ACTION = (
    "CodeLogicIncEngineering/codelogic-send-build-info-github-action@master"
)

# Use a user-specific temporary directory for logs to avoid permission issues when running via uvx
# Only create the directory when debug mode is enabled
LOGS_DIR = os.path.join(tempfile.gettempdir(), "codelogic-mcp-server")
if DEBUG_MODE:
    os.makedirs(LOGS_DIR, exist_ok=True)


def ensure_logs_dir():
    """Ensure the logs directory exists when needed for debug mode."""
    if DEBUG_MODE:
        os.makedirs(LOGS_DIR, exist_ok=True)


def get_workspace_name():
    """Get the CodeLogic workspace name from environment variable with fallback."""
    workspace_name = os.getenv("CODELOGIC_WORKSPACE_NAME")
    if not workspace_name:
        sys.stderr.write("Warning: CODELOGIC_WORKSPACE_NAME environment variable not set. Using default workspace.\n")
        workspace_name = "default-workspace"
    return workspace_name


def write_json_to_file(file_path, data):
    """Write JSON data to a file with improved formatting."""
    ensure_logs_dir()
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, separators=(", ", ": "), ensure_ascii=False, sort_keys=True)


def log_timing(operation, duration, details=""):
    """Log timing information for operations."""
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ensure_logs_dir()
        with open(os.path.join(LOGS_DIR, "timing_log.txt"), "a") as log_file:
            log_file.write(f"{timestamp} - {operation} took {duration:.4f} seconds {details}\n")


def generate_send_build_info_command(
    agent_type=None, server_host=None, platform="generic", include_platform_specific=True
):
    """Generate standardized send_build_info docker command using the dedicated image.

    agent_type and server_host are accepted for backward compatibility but ignored;
    send_build_info no longer runs from agent images (codelogic_java, etc.).
    """
    _ = agent_type  # unused; keep signature stable for callers
    _ = server_host  # server is passed via --server / CODELOGIC_HOST env

    # Platform-specific environment variables
    platform_vars = {
        "jenkins": {
            "job_name": "${JOB_NAME}",
            "build_number": "${BUILD_NUMBER}",
            "build_status": "${currentBuild.result}",
            "pipeline_system": "Jenkins",
            "workspace": "${WORKSPACE}",
        },
        "github-actions": {
            "job_name": "${{ github.repository }}",
            "build_number": "${{ github.run_number }}",
            "build_status": "${{ job.status }}",
            "pipeline_system": "GitHub Actions",
            "workspace": "${{ github.workspace }}",
        },
        "azure-devops": {
            "job_name": "$(Build.DefinitionName)",
            "build_number": "$(Build.BuildNumber)",
            "build_status": "$(Agent.JobStatus)",
            "pipeline_system": "Azure DevOps",
            "workspace": "$(Build.SourcesDirectory)",
        },
        "gitlab": {
            "job_name": "${CI_PROJECT_NAME}",
            "build_number": "${CI_PIPELINE_ID}",
            "build_status": "${CI_JOB_STATUS}",
            "pipeline_system": "GitLab CI/CD",
            "workspace": "$CI_PROJECT_DIR",
        },
        "generic": {
            "job_name": "${JOB_NAME}",
            "build_number": "${BUILD_NUMBER}",
            "build_status": "${BUILD_STATUS}",
            "pipeline_system": "CI",
            "workspace": "${WORKSPACE}",
        },
    }

    vars = platform_vars.get(platform, platform_vars["generic"])
    workspace = vars["workspace"]

    if include_platform_specific:
        return f"""docker run \\
    --pull always \\
    --rm \\
    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
    --env AGENT_UUID="${{AGENT_UUID}}" \\
    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
    --volume "{workspace}:/scan" \\
    --volume "{workspace}/logs:/log_file_path" \\
    {SEND_BUILD_INFO_IMAGE} send_build_info \\
    --agent-uuid="${{AGENT_UUID}}" \\
    --agent-password="${{AGENT_PASSWORD}}" \\
    --server="${{CODELOGIC_HOST}}" \\
    --job-name="{vars['job_name']}" \\
    --build-number="{vars['build_number']}" \\
    --build-status="{vars['build_status']}" \\
    --pipeline-system="{vars['pipeline_system']}" \\
    --log-file="/log_file_path/build.log" \\
    --log-lines=1000 \\
    --timeout=60 \\
    --verbose"""
    else:
        return f"""docker run \\
    --pull always \\
    --rm \\
    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
    --env AGENT_UUID="${{AGENT_UUID}}" \\
    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
    --volume "{workspace}:/scan" \\
    --volume "{workspace}/logs:/log_file_path" \\
    {SEND_BUILD_INFO_IMAGE} send_build_info \\
    --agent-uuid="${{AGENT_UUID}}" \\
    --agent-password="${{AGENT_PASSWORD}}" \\
    --server="${{CODELOGIC_HOST}}" \\
    --log-file="/log_file_path/build.log" \\
    --log-lines=1000 \\
    --timeout=60 \\
    --verbose"""


def generate_github_actions_send_build_info_step(log_file=None, if_condition="always()"):
    """Generate a GitHub Actions step using the send-build-info GitHub Action.

    Log files must live under the workspace (e.g. /github/workspace/logs/...) because
    the Action cannot add extra Docker volume mounts.
    """
    log_inputs = ""
    if log_file:
        log_inputs = f"""
          log_file: {log_file}
          log_lines: 1000"""

    return f"""- name: Send Build Info
      if: {if_condition}
      uses: {SEND_BUILD_INFO_GITHUB_ACTION}
      with:
          codelogic_host: ${{{{ secrets.CODELOGIC_HOST }}}}
          agent_uuid: ${{{{ secrets.AGENT_UUID }}}}
          agent_password: ${{{{ secrets.AGENT_PASSWORD }}}}
          scan_path: /github/workspace
          job_name: ${{{{ github.workflow }}}}
          build_number: ${{{{ github.run_number }}}}
          build_status: ${{{{ job.status }}}}
          pipeline_system: GitHub Actions{log_inputs}
      continue-on-error: true"""
