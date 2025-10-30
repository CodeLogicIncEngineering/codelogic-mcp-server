# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Handler for the codelogic-ci tool.
"""

import os
import sys
import mcp.types as types


async def handle_ci(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-ci tool for unified CI/CD configuration (analyze + build-info)"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    agent_type = arguments.get("agent_type")
    scan_path = arguments.get("scan_path")
    application_name = arguments.get("application_name")
    ci_platform = arguments.get("ci_platform", "generic")

    # Validate required parameters
    if not agent_type or not scan_path or not application_name:
        sys.stderr.write("Agent type, scan path, and application name are required\n")
        raise ValueError("Agent type, scan path, and application name are required")

    # Validate agent type
    valid_agent_types = ["dotnet", "java", "sql", "javascript"]
    if agent_type not in valid_agent_types:
        sys.stderr.write(f"Invalid agent type: {agent_type}. Must be one of: {', '.join(valid_agent_types)}\n")
        raise ValueError(f"Invalid agent type: {agent_type}. Must be one of: {', '.join(valid_agent_types)}")

    # Validate CI platform
    valid_ci_platforms = ["jenkins", "github-actions", "azure-devops", "gitlab", "generic"]
    if ci_platform not in valid_ci_platforms:
        sys.stderr.write(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}\n")
        raise ValueError(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}")

    # Get server configuration
    server_host = os.getenv("CODELOGIC_SERVER_HOST")
    
    # Generate Docker agent configuration based on agent type
    agent_config = generate_docker_agent_config(
        agent_type, scan_path, application_name, 
        ci_platform, server_host
    )

    return [
        types.TextContent(
            type="text",
            text=agent_config
        )
    ]


def generate_docker_agent_config(agent_type, scan_path, application_name, ci_platform, server_host):
    """Generate Docker agent configuration with AI-actionable prompts for CI/CD file modification"""
    
    # Agent type mappings
    agent_images = {
        "dotnet": "codelogic_dotnet",
        "java": "codelogic_java", 
        "sql": "codelogic_sql",
        "javascript": "codelogic_javascript"
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
        "docker_command": generate_docker_command(agent_type, scan_path, application_name, server_host, agent_image),
        "file_modifications": generate_file_modifications(ci_platform, agent_type, scan_path, application_name, server_host, agent_image),
        "setup_instructions": generate_setup_instructions(ci_platform),
        "validation_checks": generate_validation_checks(ci_platform)
    }
    
    config = f"""# CodeLogic CI Integration - Unified CI/CD Guide

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

### For CodeLogic Test Error Reporting Operations:
- **Required**: `CODELOGIC_HOST`, `AGENT_UUID`, `AGENT_PASSWORD`
- **Purpose**: Send test error reporting metadata and context to CodeLogic

### Send Test Error Reporting Command Syntax:
- **Use explicit parameters**: `--agent-uuid`, `--agent-password`, `--server`
- **Include pipeline system**: `--pipeline-system="Jenkins"`, `"GitHub Actions"`, `"Azure DevOps"`, `"GitLab CI/CD"`

#### **GitHub Actions:**
- `--job-name="${{{{ github.repository }}}}"`
- `--build-number="${{{{ github.run_number }}}}"`
- `--build-status="${{{{ job.status }}}}"`
- `--pipeline-system="GitHub Actions"`

#### **Azure DevOps:**
- `--job-name="${{{{ BUILD_DEFINITIONNAME }}}}"`
- `--build-number="${{{{ BUILD_BUILDNUMBER }}}}"`
- `--build-status="${{{{ AGENT_JOBSTATUS }}}}"`
- `--pipeline-system="Azure DevOps"`

#### **GitLab CI/CD:**
- `--job-name="${{{{ CI_PROJECT_NAME }}}}"`
- `--build-number="${{{{ CI_PIPELINE_ID }}}}"`
- `--build-status="${{{{ CI_JOB_STATUS }}}}"`
- `--pipeline-system="GitLab CI/CD"`
"""

    # Add platform-specific configurations
    if ci_platform == "jenkins":
        config += generate_jenkins_config(agent_type, scan_path, application_name, server_host)
    elif ci_platform == "github-actions":
        config += generate_github_actions_config(agent_type, scan_path, application_name, server_host)
    elif ci_platform == "azure-devops":
        config += generate_azure_devops_config(agent_type, scan_path, application_name, server_host)
    elif ci_platform == "gitlab":
        config += generate_gitlab_config(agent_type, scan_path, application_name, server_host)
    else:
        config += generate_generic_config(agent_type, scan_path, application_name, server_host)

    # Add build info section
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

3. **Security**: Store credentials as environment variables, never in code
4. **Performance**: Use `--pull always` to ensure latest agent version
5. **Logging**: Mount log directories for error reporting collection
"""

    # Append unified pipeline and best-practices guidance
    config += """

## Pipeline Overview

- CI Platforms: Jenkins, GitHub Actions, Azure DevOps, GitLab CI
- Agent Types: dotnet, java, sql, javascript
- Core Utilities: analyze (code scanning) and send_build_info (build/test log reporting)

## Build and Test Error Reporting (Two-step requirement)

1. CAPTURE logs to a file (e.g., logs/build.log)
2. SEND with send_build_info, mounting the logs folder and specifying --log-file

### Platform Flags for send_build_info

- Jenkins: --job-name="${JOB_NAME}" --build-number="${BUILD_NUMBER}" --build-status="${currentBuild.result}" --pipeline-system="Jenkins"
- GitHub Actions: --job-name="${{ github.repository }}" --build-number="${{ github.run_number }}" --build-status="${{ job.status }}" --pipeline-system="GitHub Actions"
- Azure DevOps: --job-name="$(Build.DefinitionName)" --build-number="$(Build.BuildNumber)" --build-status="$(Agent.JobStatus)" --pipeline-system="Azure DevOps"
- GitLab CI/CD: --job-name="${CI_PROJECT_NAME}" --build-number="${CI_PIPELINE_ID}" --build-status="${CI_JOB_STATUS}" --pipeline-system="GitLab CI/CD"

### Common Mistakes to Avoid

- WRONG: Sending build info without capturing logs first
- WRONG: Missing --log-file parameter
- WRONG: Not mounting logs volume (e.g., --volume "$PWD/logs:/log_file_path")
- WRONG: Jenkins step as a normal stage (should use post block)
- WRONG: Not using always() / condition: always() so failures are missed

## DevOps Best Practices

### Scan Space Management

- Choose a naming strategy (environment-, branch-, team-, or project-based)
- Replace YOUR_SCAN_SPACE_NAME consistently across pipelines

### Security Configuration (store as secrets)

```bash
CODELOGIC_HOST="https://your-instance.app.codelogic.com"
AGENT_UUID="your-agent-uuid"
AGENT_PASSWORD="your-agent-password"
SCAN_SPACE_PREFIX="your-team" # optional
```

### Error Handling Strategy

1. Scan failures: continue pipeline but mark unstable/allow_failure
2. Build info failures: log warning; do not fail pipeline
3. Network issues: retry with exponential backoff
4. Credential issues: fail fast with clear errors

### Performance Optimization

1. Parallel scans when using multiple agent types
2. Incremental scans with --rescan
3. Set Docker memory limits appropriately
4. Use Docker layer caching
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


def generate_docker_command(agent_type, scan_path, application_name, server_host, agent_image):
    """Generate the Docker command template with proper environment variable handling"""
    return f"""# CodeLogic Scan Operation - Docker Command

## Required Environment Variables (Scan Operation)
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
    --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
    --rescan \\
    --expunge-scan-sessions
```

## Important Notes
- **Only 3 environment variables are needed for the analyze operation**
- **Do NOT include JOB_NAME, BUILD_NUMBER, GIT_COMMIT, or GIT_BRANCH for scan**
- **These additional variables are only used for test error reporting operations**

## Send Build Info Command (Separate Operation)
For sending build information, use the proper `send_build_info` command:

```bash
# Standardized send_build_info command
docker run \\
    --pull always \\
    --rm \\
    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
    --env AGENT_UUID="${{AGENT_UUID}}" \\
    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
    --volume "${{WORKSPACE}}:/scan" \\
    --volume "${{WORKSPACE}}/logs:/log_file_path" \\
    ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest send_build_info \\
    --agent-uuid="${{AGENT_UUID}}" \\
    --agent-password="${{AGENT_PASSWORD}}" \\
    --server="${{CODELOGIC_HOST}}" \\
    --job-name="${{JOB_NAME}}" \\
    --build-number="${{BUILD_NUMBER}}" \\
    --build-status="${{currentBuild.result}}" \\
    --pipeline-system="Jenkins" \\
    --log-file="/log_file_path/build.log" \\
    --log-lines=1000 \\
    --timeout=60 \\
    --verbose
```

### Send Build Info Options:
- `--agent-uuid`: Required authentication
- `--agent-password`: Required authentication  
- `--server`: CodeLogic server URL
- `--job-name`: CI/CD job name (use platform-specific variables)
- `--build-number`: Build number (use platform-specific variables)
- `--build-status`: SUCCESS, FAILURE, UNSTABLE, etc. (use platform-specific variables)
- `--pipeline-system`: Jenkins, GitHub Actions, Azure DevOps, GitLab CI/CD
- `--log-file`: Path to build log file
- `--log-lines`: Number of log lines to send (default: 1000)
- `--timeout`: Network timeout in seconds (default: 60)
- `--verbose`: Extra logging"""


def generate_file_modifications(ci_platform, agent_type, scan_path, application_name, server_host, agent_image):
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
                    --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
                    --rescan \\
                    --expunge-scan-sessions
            '''
        }}
    }}
}}

// ❌ DEPRECATED: Stage-based build info (DO NOT USE)
// This approach is INCORRECT because:
// - Won't run if earlier stages fail
// - Can't reliably capture final build status
// - Misses console output from failed builds
// 
// Use the post block approach below instead!

// RECOMMENDED: Use post block for build info
// This ensures build info is sent even on failures and captures final status

post {{
    always {{
        script {{
            // Only send build info for main/develop/feature branches
            if (env.BRANCH_NAME ==~ /(main|develop|feature\\/.*)/) {{
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {{
                    // STEP 1: Create logs directory and capture build information
                    sh '''
                        mkdir -p ${{WORKSPACE}}/logs
                        
                        # Capture comprehensive build information
                        echo "=== Build Information ===" > ${{WORKSPACE}}/logs/build.log
                        echo "Build Date: \$(date)" >> ${{WORKSPACE}}/logs/build.log
                        echo "Job Name: ${{JOB_NAME}}" >> ${{WORKSPACE}}/logs/build.log
                        echo "Build Number: ${{BUILD_NUMBER}}" >> ${{WORKSPACE}}/logs/build.log
                        echo "Branch: ${{BRANCH_NAME}}" >> ${{WORKSPACE}}/logs/build.log
                        echo "Git Commit: ${{GIT_COMMIT}}" >> ${{WORKSPACE}}/logs/build.log
                        echo "Build Result: ${{currentBuild.result ?: 'SUCCESS'}}" >> ${{WORKSPACE}}/logs/build.log
                        echo "" >> ${{WORKSPACE}}/logs/build.log
                        
                        # Capture console output header
                        echo "=== Build Console Output ===" >> ${{WORKSPACE}}/logs/build.log
                    '''
                    
                    // STEP 2: Capture Jenkins console log (last 1000 lines)
                    def consoleLog = currentBuild.rawBuild.getLog(1000)
                    writeFile file: "${{WORKSPACE}}/logs/console_output.txt", text: consoleLog.join('\\n')
                    
                    sh '''
                        cat ${{WORKSPACE}}/logs/console_output.txt >> ${{WORKSPACE}}/logs/build.log
                    '''
                    
                    // STEP 3: Send build info with captured logs to CodeLogic
                    def buildStatus = currentBuild.result ?: 'SUCCESS'
                    echo "Sending build info with status: ${{buildStatus}}"
                    
                    sh '''
                        docker run \\
                            --pull always \\
                            --rm \\
                            --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                            --env AGENT_UUID="${{AGENT_UUID}}" \\
                            --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                            --volume "${{WORKSPACE}}:/scan" \\
                            --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                            ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest send_build_info \\
                            --agent-uuid="${{AGENT_UUID}}" \\
                            --agent-password="${{AGENT_PASSWORD}}" \\
                            --server="${{CODELOGIC_HOST}}" \\
                            --job-name="${{JOB_NAME}}" \\
                            --build-number="${{BUILD_NUMBER}}" \\
                            --build-status="${{buildStatus}}" \\
                            --pipeline-system="Jenkins" \\
                            --log-file="/log_file_path/build.log" \\
                            --log-lines=1000 \\
                            --timeout=60 \\
                            --verbose
                    '''
                }}
            }}
        }}
    }}
}}

// WHY USE POST BLOCK?
// ✅ Runs after all stages complete (captures final status)
// ✅ Always executes (runs even if build fails - critical for error reporting!)
// ✅ Access to full console logs (can capture complete error output)
// ✅ Proper build status (currentBuild.result is accurate here)
// ❌ Stage-based approach: Won't run if earlier stages fail, can't capture final status"""
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
          --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
      
    - name: Send Build Info
      if: always()
      run: |
        # Create logs directory
        mkdir -p logs
        
        # Capture build information
        echo "Build completed at: $(date)" > logs/build.log
        echo "Repository: ${{{{ github.repository }}}}" >> logs/build.log
        echo "Workflow: ${{{{ github.workflow }}}}" >> logs/build.log
        echo "Run Number: ${{{{ github.run_number }}}}" >> logs/build.log
        echo "Commit: ${{{{ github.sha }}}}" >> logs/build.log
        echo "Branch: ${{{{ github.ref_name }}}}" >> logs/build.log
        echo "Build Status: ${{{{ job.status }}}}" >> logs/build.log
        
        # Send build info with proper command syntax
        docker run \\
          --pull always \\
          --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --agent-uuid="${{{{ secrets.AGENT_UUID }}}}" \\
          --agent-password="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --server="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --job-name="${{{{ github.repository }}}}" \\
          --build-number="${{{{ github.run_number }}}}" \\
          --build-status="${{{{ job.status }}}}" \\
          --pipeline-system="GitHub Actions" \\
          --log-file="/log_file_path/build.log" \\
          --log-lines=1000 \\
          --timeout=60 \\
          --verbose
      continue-on-error: true"""
                }
            ]
        },
        "azure-devops": {
            "file": "azure-pipelines.yml",
            "modifications": [
                {
                    "type": "create_file",
                    "content": f"""trigger:
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
          --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
          --rescan \\
          --expunge-scan-sessions
      continueOnError: true
      
    - task: Docker@2
      displayName: 'Send Build Info'
      condition: always()
      inputs:
        command: 'run'
        arguments: |
          --pull always \\
          --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          --volume "$(Build.SourcesDirectory)/logs:/log_file_path" \\
          $(codelogicHost)/codelogic_{agent_type}:latest send_build_info \\
          --agent-uuid="$(agentUuid)" \\
          --agent-password="$(agentPassword)" \\
          --server="$(codelogicHost)" \\
          --job-name="$(Build.DefinitionName)" \\
          --build-number="$(Build.BuildNumber)" \\
          --build-status="$(Agent.JobStatus)" \\
          --pipeline-system="Azure DevOps" \\
          --log-file="/log_file_path/build.log" \\
          --log-lines=1000 \\
          --timeout=60 \\
          --verbose
      continueOnError: true
      
    - task: PublishBuildArtifacts@1
      displayName: 'Publish Build Logs'
      inputs:
        pathToPublish: 'logs'
        artifactName: 'build-logs'
      condition: always()"""
                }
            ]
        },
        "gitlab": {
            "file": ".gitlab-ci.yml",
            "modifications": [
                {
                    "type": "create_file",
                    "content": f"""stages:
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
        --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
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
      # Create logs directory
      mkdir -p logs
      
      # Capture build information
      echo "Build completed at: $(date)" > logs/build.log
      echo "Project: $CI_PROJECT_NAME" >> logs/build.log
      echo "Pipeline: $CI_PIPELINE_ID" >> logs/build.log
      echo "Job: $CI_JOB_NAME" >> logs/build.log
      echo "Commit: $CI_COMMIT_SHA" >> logs/build.log
      echo "Branch: $CI_COMMIT_REF_NAME" >> logs/build.log
      echo "Build Status: $CI_JOB_STATUS" >> logs/build.log
      
      # Send build info with proper command syntax
      docker run \\
        --pull always \\
        --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        --volume "$CI_PROJECT_DIR/logs:/log_file_path" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest send_build_info \\
        --agent-uuid="$AGENT_UUID" \\
        --agent-password="$AGENT_PASSWORD" \\
        --server="$CODELOGIC_HOST" \\
        --job-name="$CI_PROJECT_NAME" \\
        --build-number="$CI_PIPELINE_ID" \\
        --build-status="$CI_JOB_STATUS" \\
        --pipeline-system="GitLab CI/CD" \\
        --log-file="/log_file_path/build.log" \\
        --log-lines=1000 \\
        --timeout=60 \\
        --verbose
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"
  allow_failure: true
  artifacts:
    paths:
      - logs/
    expire_in: 30 days"""
                }
            ]
        }
    }
    return modifications.get(ci_platform, {})


def generate_setup_instructions(ci_platform):
    """Generate setup instructions for each platform"""
    instructions = {
        "jenkins": [
            "1. Go to Jenkins → Manage Jenkins → Manage Credentials",
            "2. Add Secret Text credentials: codelogic-agent-uuid, codelogic-agent-password",
            "3. Install Docker Pipeline Plugin if not already installed",
            "4. Configure build triggers for main, develop, and feature branches",
            "5. Test the pipeline with a sample build"
        ],
        "github-actions": [
            "1. Go to repository Settings → Secrets and variables → Actions",
            "2. Add repository secrets: CODELOGIC_HOST, AGENT_UUID, AGENT_PASSWORD",
            "3. Ensure Docker is available in runner (default for ubuntu-latest)",
            "4. Configure branch triggers for main, develop, and feature branches",
            "5. Test the workflow with a sample commit"
        ],
        "azure-devops": [
            "1. Go to pipeline variables and add: codelogicAgentUuid, codelogicAgentPassword",
            "2. Mark variables as secret",
            "3. Ensure Docker task is available",
            "4. Configure build triggers for main, develop, and feature branches",
            "5. Test the pipeline with a sample build"
        ],
        "gitlab": [
            "1. Go to Settings → CI/CD → Variables",
            "2. Add variables: AGENT_UUID, AGENT_PASSWORD",
            "3. Mark as protected and masked",
            "4. Ensure Docker-in-Docker is enabled",
            "5. Configure branch rules for main, develop, and feature branches",
            "6. Test the pipeline with a sample commit"
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


def generate_jenkins_config(agent_type, scan_path, application_name, server_host):
    """Generate Jenkins-specific configuration with AI modification prompts"""
    
    # Technology-specific guidance based on agent type
    tech_guidance = {
        'dotnet': {
            'build_command': 'dotnet build',
            'test_command': 'dotnet test',
            'env_info': 'dotnet --version && dotnet --info',
            'artifacts': '*.dll, *.exe, *.so',
            'test_results': 'TestResults/**/*.trx'
        },
        'java': {
            'build_command': 'mvn clean compile',
            'test_command': 'mvn test',
            'env_info': 'java -version && mvn -version',
            'artifacts': '*.jar, *.war, *.ear',
            'test_results': 'target/surefire-reports/**/*.xml'
        },
        'javascript': {
            'build_command': 'npm run build',
            'test_command': 'npm test',
            'env_info': 'node --version && npm --version',
            'artifacts': 'dist/**, build/**, *.js',
            'test_results': 'coverage/**, test-results/**'
        }
    }
    
    tech_info = tech_guidance.get(agent_type, tech_guidance['java'])  # Default to Java
    
    return f"""
### 🎯 Jenkins File Modification Guide

**AI Prompt: "Modify the Jenkinsfile to add CodeLogic scanning for {agent_type.upper()} applications"**

**CRITICAL INSTRUCTIONS FOR AI:**
1. **You MUST modify existing build and test stages** to capture logs to files
2. **Choose the appropriate log capture method based on the CI platform and OS**:
   - For Linux/Unix agents: Use `tee`, redirection, or shell logging
   - For Windows agents: Use PowerShell Tee-Object, redirection, or similar
   - For cross-platform: Consider the agent's actual OS or provide platform-specific examples
3. **Do NOT just add new stages** - modify the existing ones to include log capture
4. **The log capture is REQUIRED, not optional** - CodeLogic needs these logs for analysis
5. **Use BEFORE/AFTER examples** to show exactly what to change

## ⚠️ IMPORTANT: Scan Space Name Required

**Before implementing CodeLogic integration, you MUST determine the scan space name.**

### Check if scan space is already defined:
Look for existing scan space configuration in your CI file:
- Search for `SCAN_SPACE`, `scan_space_name`, or similar variables
- Look for CodeLogic-related environment variables
- Check if there are existing CodeLogic integration patterns

### If scan space is NOT explicitly defined:
**You MUST ask the user to provide a scan space name before proceeding.**

**Ask the user: "What scan space name should be used for CodeLogic scans? (e.g., 'Development', 'Production', 'Team-Frontend')"**

**Do NOT proceed with CodeLogic integration until you have a scan space name from the user.**

#### Step 1: Add Environment Variables
Add this to the `environment` block in your Jenkinsfile:

```groovy
environment {{
    CODELOGIC_HOST = '{server_host}'
    CODELOGIC_IMAGE = '${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest'
    AGENT_UUID = credentials('codelogic-agent-uuid')
    AGENT_PASSWORD = credentials('codelogic-agent-password')
}}
```

#### Step 2: **REQUIRED** - Modify Existing Build Stages to Capture Logs

**CRITICAL**: You MUST modify your existing build stages to capture build and test logs. This is not optional - CodeLogic needs these logs for proper analysis.

**Find your existing build stages** (like `stage('Build')`, `stage('Unit Test')`, etc.) and modify them to capture logs:

**Platform-Specific Log Capture Guidance:**
- **Linux/Unix agents**: Use `tee` command (e.g., `{tech_info['build_command']} 2>&1 | tee logs/build.log`)
- **Windows agents**: Use PowerShell (e.g., `{tech_info['build_command']} 2>&1 | Tee-Object -FilePath logs/build.log`)
- **Cross-platform**: Detect the OS and use appropriate method, or use redirection (e.g., `{tech_info['build_command']} > logs/build.log 2>&1`)

```groovy
// BEFORE: Your existing build stage
stage('Build') {{
    steps {{
        sh 'dotnet build'
    }}
}}

// AFTER: Modified to capture logs (Linux/Unix example with tee)
stage('Build') {{
    steps {{
        sh '''
            # Create logs directory
            mkdir -p logs
            
            # Capture build output AND continue with normal build
            # Choose appropriate log capture based on your CI agent OS:
            # Linux/Unix: use tee command
            {tech_info['build_command']} 2>&1 | tee logs/build.log
            
            # Capture environment info for CodeLogic
            echo "=== Environment Information ===" > logs/build-info.log
            echo "Build Time: $(date)" >> logs/build-info.log
            echo "Branch: ${{BRANCH_NAME}}" >> logs/build-info.log
            echo "Commit: ${{GIT_COMMIT}}" >> logs/build-info.log
            {tech_info['env_info']} >> logs/build-info.log
        '''
    }}
}}

// ALTERNATIVE: For Windows PowerShell agents
stage('Build') {{
    steps {{
        powershell '''
            # Create logs directory
            New-Item -ItemType Directory -Force -Path logs
            
            # Capture build output using PowerShell Tee-Object
            {tech_info['build_command']} 2>&1 | Tee-Object -FilePath logs/build.log
            
            # Capture environment info for CodeLogic
            "=== Environment Information ===" | Out-File logs/build-info.log
            "Build Time: $(Get-Date)" | Out-File -Append logs/build-info.log
            "Branch: ${{env:BRANCH_NAME}}" | Out-File -Append logs/build-info.log
            "Commit: ${{env:GIT_COMMIT}}" | Out-File -Append logs/build-info.log
            {tech_info['env_info']} | Out-File -Append logs/build-info.log
        '''
    }}
}}
```

#### Step 3: **REQUIRED** - Modify Existing Test Stages to Capture Logs

**CRITICAL**: You MUST modify your existing test stages to capture test logs and results.

```groovy
// BEFORE: Your existing test stage
stage('Unit Test') {{
    steps {{
        sh 'dotnet test'
    }}
}}

// AFTER: Modified to capture logs (Linux/Unix example)
stage('Unit Test') {{
    steps {{
        sh '''
            # Capture test output AND continue with normal tests
            # Choose appropriate log capture based on your CI agent OS:
            # Linux/Unix: use tee command
            {tech_info['test_command']} 2>&1 | tee logs/test.log
            
            # Archive test results for CodeLogic
            archiveArtifacts artifacts: '{tech_info['test_results']}', allowEmptyArchive: true
        '''
    }}
}}

// ALTERNATIVE: For Windows PowerShell agents
stage('Unit Test') {{
    steps {{
        powershell '''
            # Capture test output using PowerShell Tee-Object
            {tech_info['test_command']} 2>&1 | Tee-Object -FilePath logs/test.log
            
            # Archive test results for CodeLogic
            archiveArtifacts artifacts: '{tech_info['test_results']}', allowEmptyArchive: true
        '''
    }}
}}
```

**IMPORTANT**: Log capture methods (tee, Tee-Object, redirection) will:
- ✅ **Continue your normal build/test process** (output goes to console)
- ✅ **Save a copy to log files** (for CodeLogic analysis)
- ✅ **Not break your existing pipeline** (if build fails, pipeline still fails)
- ⚠️ **Choose the right method for your CI agent OS** (Linux/Unix vs Windows)

#### Example for .NET Projects:

If you have existing .NET build stages like this:
```groovy
stage('Build netCape') {{
    steps {{
        sh '''
            dotnet restore
            dotnet publish -c Release -p:Version=$MAVEN_PUBLISH_VERSION
        '''
    }}
}}
```

**MODIFY them to this (Linux/Unix example):**
```groovy
stage('Build netCape') {{
    steps {{
        sh '''
            mkdir -p logs
            dotnet restore
            # Use tee for Linux/Unix agents, or adjust for Windows
            dotnet publish -c Release -p:Version=$MAVEN_PUBLISH_VERSION 2>&1 | tee logs/build.log
            echo "=== Environment Information ===" > logs/build-info.log
            echo "Build Time: $(date)" >> logs/build-info.log
            echo "Branch: ${{BRANCH_NAME}}" >> logs/build-info.log
            echo "Commit: ${{GIT_COMMIT}}" >> logs/build-info.log
            dotnet --version >> logs/build-info.log
            dotnet --info >> logs/build-info.log
        '''
    }}
}}
```

**ALTERNATIVE for Windows agents:**
```groovy
stage('Build netCape') {{
    steps {{
        powershell '''
            New-Item -ItemType Directory -Force -Path logs
            dotnet restore
            # Use Tee-Object for Windows PowerShell agents
            dotnet publish -c Release -p:Version=${{env:MAVEN_PUBLISH_VERSION}} 2>&1 | Tee-Object -FilePath logs/build.log
            "=== Environment Information ===" | Out-File logs/build-info.log
            "Build Time: $(Get-Date)" | Out-File -Append logs/build-info.log
            "Branch: ${{env:BRANCH_NAME}}" | Out-File -Append logs/build-info.log
            "Commit: ${{env:GIT_COMMIT}}" | Out-File -Append logs/build-info.log
            dotnet --version | Out-File -Append logs/build-info.log
            dotnet --info | Out-File -Append logs/build-info.log
        '''
    }}
}}
```

#### Step 4: Add CodeLogic Build Info Collection Stage
Insert this stage after your build/test stages:

```groovy
stage('CodeLogic Build Info Collection') {{
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
                mkdir -p logs
                
                # Collect comprehensive build information
                echo "=== Build Information ===" > logs/codelogic-build.log
                echo "Job: ${{JOB_NAME}}" >> logs/codelogic-build.log
                echo "Build: ${{BUILD_NUMBER}}" >> logs/codelogic-build.log
                echo "Branch: ${{BRANCH_NAME}}" >> logs/codelogic-build.log
                echo "Commit: ${{GIT_COMMIT}}" >> logs/codelogic-build.log
                echo "" >> logs/codelogic-build.log
                
                # Append build logs if they exist
                [ -f build.log ] && echo "=== Build Log ===" >> logs/codelogic-build.log && cat build.log >> logs/codelogic-build.log
                [ -f test.log ] && echo "=== Test Log ===" >> logs/codelogic-build.log && cat test.log >> logs/codelogic-build.log
                
                # Send to CodeLogic
                docker run --rm \\
                    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                    --env AGENT_UUID="${{AGENT_UUID}}" \\
                    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                    --volume "${{WORKSPACE}}:/scan" \\
                    --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                    ${{CODELOGIC_IMAGE}} send_build_info \\
                    --agent-uuid="${{AGENT_UUID}}" \\
                    --agent-password="${{AGENT_PASSWORD}}" \\
                    --server="${{CODELOGIC_HOST}}" \\
                    --job-name="${{JOB_NAME}}" \\
                    --build-number="${{BUILD_NUMBER}}" \\
                    --build-status="${{currentBuild.result}}" \\
                    --pipeline-system="Jenkins" \\
                    --log-file="/log_file_path/codelogic-build.log" \\
                    --log-lines=1000 \\
                    --timeout=60 \\
                    --verbose
            '''
        }}
    }}
}}
```

#### Step 5: Add CodeLogic Scan Stage
Insert this stage after your build info collection:

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
                # Determine scan space name based on branch
                if [[ "${{BRANCH_NAME}}" =~ ^(main|develop|master)$ ]]; then
                    SCAN_SPACE="YOUR_SCAN_SPACE_NAME-${{BRANCH_NAME}}"
                else
                    SCAN_SPACE="YOUR_SCAN_SPACE_NAME-${{BRANCH_NAME}}-${{BUILD_NUMBER}}"
                fi
                
                echo "Starting CodeLogic {agent_type} scan..."
                echo "Application: {application_name}"
                echo "Scan Space: $SCAN_SPACE"
                echo "Target Path: {scan_path}"
                
                docker run --pull always --rm --interactive \\
                    --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                    --env AGENT_UUID="${{AGENT_UUID}}" \\
                    --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                    --volume "${{WORKSPACE}}:/scan" \\
                    ${{CODELOGIC_IMAGE}} analyze \\
                    --application "{application_name}" \\
                    --path "/scan/{scan_path}" \\
                    --scan-space-name "$SCAN_SPACE" \\
                    --rescan \\
                    --expunge-scan-sessions \\
                    --verbose
            '''
        }}
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
                            --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
                            --rescan \\
                            --expunge-scan-sessions
                    '''
                }}
            }}
        }}
        
        stage('Send Build Info') {{
            steps {{
                sh '''
                    docker run --rm \\
                        --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                        --env AGENT_UUID="${{AGENT_UUID}}" \\
                        --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
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


def generate_github_actions_config(agent_type, scan_path, application_name, server_host):
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
          --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
      
    - name: Send Build Info
      if: always()
      run: |
        docker run \\
          --pull always \\
          --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --agent-uuid="${{{{ secrets.AGENT_UUID }}}}" \\
          --agent-password="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --server="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --job-name="${{{{ github.repository }}}}" \\
          --build-number="${{{{ github.run_number }}}}" \\
          --build-status="${{{{ job.status }}}}" \\
          --pipeline-system="GitHub Actions" \\
          --log-file="/log_file_path/build.log" \\
          --log-lines=1000 \\
          --timeout=60 \\
          --verbose
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
      --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
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
          --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
      
    - name: Send Build Info
      if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
      run: |
        docker run \\
          --pull always \\
          --rm \\
          --env CODELOGIC_HOST="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ secrets.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ secrets.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --agent-uuid="${{{{ secrets.AGENT_UUID }}}}" \\
          --agent-password="${{{{ secrets.AGENT_PASSWORD }}}}" \\
          --server="${{{{ secrets.CODELOGIC_HOST }}}}" \\
          --job-name="${{{{ github.repository }}}}" \\
          --build-number="${{{{ github.run_number }}}}" \\
          --build-status="${{{{ job.status }}}}" \\
          --pipeline-system="GitHub Actions" \\
          --log-file="/log_file_path/build.log" \\
          --log-lines=1000 \\
          --timeout=60 \\
          --verbose
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


def generate_azure_devops_config(agent_type, scan_path, application_name, server_host):
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
          --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
          --rescan \\
          --expunge-scan-sessions
      continueOnError: true
      
    - task: Docker@2
      displayName: 'Send Build Info'
      condition: always()
      inputs:
        command: 'run'
        arguments: |
          --pull always \\
          --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          --volume "$(Build.SourcesDirectory)/logs:/log_file_path" \\
          $(codelogicHost)/codelogic_{agent_type}:latest send_build_info \\
          --agent-uuid="$(agentUuid)" \\
          --agent-password="$(agentPassword)" \\
          --server="$(codelogicHost)" \\
          --job-name="$(Build.DefinitionName)" \\
          --build-number="$(Build.BuildNumber)" \\
          --build-status="$(Agent.JobStatus)" \\
          --pipeline-system="Azure DevOps" \\
          --log-file="/log_file_path/build.log" \\
          --log-lines=1000 \\
          --timeout=60 \\
          --verbose
      continueOnError: true
      
    - task: PublishBuildArtifacts@1
      displayName: 'Publish Build Logs'
      inputs:
        pathToPublish: 'logs'
        artifactName: 'build-logs'
      condition: always()
```

### Azure DevOps Variables

Add these variables to your pipeline:
- `codelogicAgentUuid`: Your agent UUID (mark as secret)
- `codelogicAgentPassword`: Your agent password (mark as secret)
"""


def generate_gitlab_config(agent_type, scan_path, application_name, server_host):
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
        --scan-space-name "YOUR_SCAN_SPACE_NAME" \\
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
      docker run \\
        --pull always \\
        --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        --volume "$CI_PROJECT_DIR/logs:/log_file_path" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest send_build_info \\
        --agent-uuid="$AGENT_UUID" \\
        --agent-password="$AGENT_PASSWORD" \\
        --server="$CODELOGIC_HOST" \\
        --job-name="$CI_PROJECT_NAME" \\
        --build-number="$CI_PIPELINE_ID" \\
        --build-status="$CI_JOB_STATUS" \\
        --pipeline-system="GitLab CI/CD" \\
        --log-file="/log_file_path/build.log" \\
        --log-lines=1000 \\
        --timeout=60 \\
        --verbose
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


def generate_generic_config(agent_type, scan_path, application_name, server_host):
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
SCAN_SPACE="${{SCAN_SPACE:-YOUR_SCAN_SPACE_NAME}}"

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
