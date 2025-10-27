# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Handler for the codelogic-build-info tool.
"""

import sys
import mcp.types as types


async def handle_build_info(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-build-info tool for build information management"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    ci_platform = arguments.get("ci_platform")
    output_format = arguments.get("output_format", "docker")

    # Validate required parameters
    if not ci_platform:
        sys.stderr.write("CI platform is required\n")
        raise ValueError("CI platform is required")

    # Validate CI platform
    valid_ci_platforms = ["jenkins", "github-actions", "azure-devops", "gitlab"]
    if ci_platform not in valid_ci_platforms:
        sys.stderr.write(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}\n")
        raise ValueError(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}")

    # Validate output format
    valid_output_formats = ["docker", "standalone", "jenkins", "yaml"]
    if output_format not in valid_output_formats:
        sys.stderr.write(f"Invalid output format: {output_format}. Must be one of: {', '.join(valid_output_formats)}\n")
        raise ValueError(f"Invalid output format: {output_format}. Must be one of: {', '.join(valid_output_formats)}")

    # Generate build info configuration
    build_info_config = generate_build_info_config(
        ci_platform, output_format
    )

    return [
        types.TextContent(
            type="text",
            text=build_info_config
        )
    ]


def generate_build_info_config(ci_platform, output_format):
    """Generate build information configuration with improved accuracy"""
    
    config = f"""# CodeLogic Build Information Configuration

## Build and Test Error Reporting

**Important**: Build information is sent SEPARATELY from the main scan. This is for collecting build metadata, logs, and Git information to enhance CodeLogic analysis.

### Standardized send_build_info Command

```bash
# Complete build information collection
docker run \\
    --pull always \\
    --rm \\
    --interactive \\
    --tty \\
    --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
    --env AGENT_UUID="$AGENT_UUID" \\
    --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
    --volume "$PWD:/scan" \\
    --volume "$PWD/logs:/log_file_path" \\
    your-codelogic-image send_build_info \\
    --agent-uuid="$AGENT_UUID" \\
    --agent-password="$AGENT_PASSWORD" \\
    --server="$CODELOGIC_HOST" \\
    --log-file="/log_file_path/build.log" \\
    --log-lines=1000 \\
    --timeout=60 \\
    --verbose
```

### Platform-Specific Variables

#### Jenkins
- `--job-name="${{JOB_NAME}}"`
- `--build-number="${{BUILD_NUMBER}}"`
- `--build-status="${{currentBuild.result}}"`
- `--pipeline-system="Jenkins"`

#### GitHub Actions
- `--job-name="${{{{ github.repository }}}}"`
- `--build-number="${{{{ github.run_number }}}}"`
- `--build-status="${{{{ job.status }}}}"`
- `--pipeline-system="GitHub Actions"`

#### Azure DevOps
- `--job-name="${{BUILD_DEFINITIONNAME}}"`
- `--build-number="${{BUILD_BUILDNUMBER}}"`
- `--build-status="${{AGENT_JOBSTATUS}}"`
- `--pipeline-system="Azure DevOps"`

#### GitLab CI/CD
- `--job-name="${{CI_PROJECT_NAME}}"`
- `--build-number="${{CI_PIPELINE_ID}}"`
- `--build-status="${{CI_JOB_STATUS}}"`
- `--pipeline-system="GitLab CI/CD"`

### Required Parameters
- `--agent-uuid`: Required authentication
- `--agent-password`: Required authentication  
- `--server`: CodeLogic server URL
- `--log-file`: Path to build log file

### Optional Parameters
- `--job-name`: CI/CD job name (use platform-specific variables)
- `--build-number`: Build number (use platform-specific variables)
- `--build-status`: SUCCESS, FAILURE, UNSTABLE, etc. (use platform-specific variables)
- `--pipeline-system`: Jenkins, GitHub Actions, Azure DevOps, GitLab CI/CD
- `--log-lines`: Number of log lines to send (default: 1000)
- `--timeout`: Network timeout in seconds (default: 60)
- `--verbose`: Extra logging
"""

    return config
