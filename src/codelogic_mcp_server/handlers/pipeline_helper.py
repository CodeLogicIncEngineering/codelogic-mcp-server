# Copyright (C) 2025 CodeLogic Inc.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Handler for the codelogic-pipeline-helper tool.
"""

import sys
import mcp.types as types


async def handle_pipeline_helper(arguments: dict | None) -> list[types.TextContent]:
    """Handle the codelogic-pipeline-helper tool for complete CI/CD pipeline configuration"""
    if not arguments:
        sys.stderr.write("Missing arguments\n")
        raise ValueError("Missing arguments")

    ci_platform = arguments.get("ci_platform")
    agent_type = arguments.get("agent_type")

    # Validate required parameters
    if not ci_platform:
        sys.stderr.write("CI platform is required\n")
        raise ValueError("CI platform is required")

    # Validate CI platform
    valid_ci_platforms = ["jenkins", "github-actions", "azure-devops", "gitlab"]
    if ci_platform not in valid_ci_platforms:
        sys.stderr.write(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}\n")
        raise ValueError(f"Invalid CI platform: {ci_platform}. Must be one of: {', '.join(valid_ci_platforms)}")

    # Generate pipeline configuration
    pipeline_config = generate_pipeline_config(
        ci_platform
    )

    return [
        types.TextContent(
            type="text",
            text=pipeline_config
        )
    ]


def generate_pipeline_config(ci_platform, agent_type="dotnet", scan_triggers=["main", "develop", "feature/*"]):
    """Generate complete pipeline configuration"""
    
    config = f"""# Complete CodeLogic CI/CD Pipeline Configuration

## Pipeline Overview

- **CI Platform**: {ci_platform.upper()}
- **Agent Type**: {agent_type.upper()}
- **Scan Triggers**: {', '.join(scan_triggers)}

"""

    if ci_platform == "jenkins":
        config += generate_jenkins_pipeline(agent_type, scan_triggers)
    elif ci_platform == "github-actions":
        config += generate_github_actions_pipeline(agent_type, scan_triggers)
    elif ci_platform == "azure-devops":
        config += generate_azure_devops_pipeline(agent_type, scan_triggers)
    elif ci_platform == "gitlab":
        config += generate_gitlab_pipeline(agent_type, scan_triggers)
    
    config += f"""

## DevOps Best Practices

### Scan Space Management

**IMPORTANT**: Before implementing this pipeline, you MUST determine your scan space naming strategy.

#### Scan Space Naming Options:

1. **Environment-based**: `Development`, `Staging`, `Production`
2. **Branch-based**: `main`, `develop`, `feature-auth`
3. **Team-based**: `Frontend-Team`, `Backend-Team`
4. **Project-based**: `Project-Alpha`, `Project-Beta`

#### Implementation:
- Replace `YOUR_SCAN_SPACE_NAME` in the pipeline with your chosen naming strategy
- Consider using CI/CD variables like `${{JOB_NAME}}` or `${{PROJECT_NAME}}`
- Ensure consistency across all environments

### Security Configuration

```bash
# Environment Variables (store as secrets)
CODELOGIC_HOST="https://your-instance.app.codelogic.com"
AGENT_UUID="your-agent-uuid"
AGENT_PASSWORD="your-agent-password"

# Optional: Custom scan space naming
SCAN_SPACE_PREFIX="your-team"
```

### Error Handling Strategy

1. **Scan Failures**: Continue pipeline but mark as unstable
2. **Build Info Failures**: Log warnings but don't fail pipeline
3. **Network Issues**: Retry with exponential backoff
4. **Credential Issues**: Fail fast with clear error messages

### Performance Optimization

1. **Parallel Scanning**: Run multiple agent types simultaneously
2. **Incremental Scans**: Use `--rescan` for faster subsequent scans
3. **Resource Limits**: Set appropriate Docker memory limits
4. **Cache Management**: Use Docker layer caching for agent images

### Monitoring and Alerting

"""

    return config


def generate_jenkins_pipeline(agent_type, scan_triggers):
    """Generate complete Jenkins pipeline"""
    trigger_conditions = " || ".join([f"branch '{trigger}'" for trigger in scan_triggers])
    
    return f"""
### Complete Jenkins Pipeline

```groovy
pipeline {{
    agent any
    
    environment {{
        CODELOGIC_HOST = 'https://your-instance.app.codelogic.com'
        AGENT_UUID = credentials('codelogic-agent-uuid')
        AGENT_PASSWORD = credentials('codelogic-agent-password')
    }}
    
    parameters {{
        choice(
            name: 'SCAN_SPACE_NAME',
            choices: ['Development', 'Staging', 'Production'],
            description: 'Target scan space for this run'
        )
    }}
    
    stages {{
        stage('CodeLogic Scan') {{
            when {{
                anyOf {{
                    {trigger_conditions}
                }}
            }}
            steps {{
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {{
                    sh '''
                        echo "Starting CodeLogic {agent_type} scan..."
                        docker run --pull always --rm --interactive \\
                            --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                            --env AGENT_UUID="${{AGENT_UUID}}" \\
                            --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                            --volume "${{WORKSPACE}}:/scan" \\
                            ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest analyze \\
                            --application "${{JOB_NAME}}" \\
                            --path /scan \\
                            --scan-space-name "${{SCAN_SPACE}}" \\
                            --rescan \\
                            --expunge-scan-sessions
                    '''
                }}
            }}
        }}
        
        stage('Send Build Info') {{
            steps {{
                sh '''
                    echo "Sending build information to CodeLogic..."
                    docker run --rm \\
                        --env CODELOGIC_HOST="${{CODELOGIC_HOST}}" \\
                        --env AGENT_UUID="${{AGENT_UUID}}" \\
                        --env AGENT_PASSWORD="${{AGENT_PASSWORD}}" \\
                        --volume "${{WORKSPACE}}:/scan" \\
                        --volume "${{WORKSPACE}}/logs:/log_file_path" \\
                        ${{CODELOGIC_HOST}}/codelogic_{agent_type}:latest send_build_info \\
                        --log-file="/log_file_path/build.log" \\
                        --job-name="${{JOB_NAME}}" \\
                        --build-number="${{BUILD_NUMBER}}"
                '''
            }}
        }}
    }}
    
    post {{
        always {{
            archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'logs',
                reportFiles: 'build.log',
                reportName: 'Build Logs'
            ])
        }}
        success {{
            echo "CodeLogic scan completed successfully"
        }}
        failure {{
            echo "CodeLogic scan failed - check logs for details"
        }}
    }}
}}
```

### Jenkins Configuration Steps

1. **Install Required Plugins**:
   - Docker Pipeline Plugin
   - HTML Publisher Plugin
   - Credentials Plugin

2. **Configure Credentials**:
   - Go to Manage Jenkins → Manage Credentials
   - Add Secret Text credentials:
     - ID: `codelogic-agent-uuid`
     - ID: `codelogic-agent-password`

3. **Configure Docker**:
   - Ensure Docker is available on Jenkins agents
   - Configure Docker daemon access for Jenkins user

4. **Set up Notifications** (if enabled):
   - Configure Slack/Teams integration
   - Set up email notifications for failures
"""


def generate_github_actions_pipeline(agent_type, scan_triggers):
    """Generate complete GitHub Actions pipeline"""
    return f"""
### Complete GitHub Actions Workflow

Create `.github/workflows/codelogic-pipeline.yml`:

```yaml
name: CodeLogic CI/CD Pipeline

on:
  push:
    branches: {scan_triggers}
  pull_request:
    branches: [ main, develop ]

env:
  CODELOGIC_HOST: ${{{{ secrets.CODELOGIC_HOST }}}}
  AGENT_UUID: ${{{{ secrets.AGENT_UUID }}}}
  AGENT_PASSWORD: ${{{{ secrets.AGENT_PASSWORD }}}}

jobs:
  codelogic-scan:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        agent-type: [{agent_type}]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full git history for better analysis
    
    - name: Determine scan space
      id: scan-space
      run: |
        if [[ "${{{{ github.ref_name }}}}" =~ ^(main|develop|master)$ ]]; then
          echo "space=YOUR_SCAN_SPACE_NAME-${{{{ github.ref_name }}}}" >> $GITHUB_OUTPUT
        else
          echo "space=YOUR_SCAN_SPACE_NAME-${{{{ github.ref_name }}}}-${{{{ github.run_number }}}}" >> $GITHUB_OUTPUT
        fi
    
    - name: CodeLogic Scan
      run: |
        echo "Starting CodeLogic ${{{{ matrix.agent-type }}}} scan..."
        docker run --pull always --rm \\
          --env CODELOGIC_HOST="${{{{ env.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ env.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ env.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          ${{{{ env.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest analyze \\
          --application "${{{{ github.repository }}}}" \\
          --path /scan \\
          --scan-space-name "${{{{ steps.scan-space.outputs.space }}}}" \\
          --rescan \\
          --expunge-scan-sessions
      continue-on-error: true
    
    - name: Send Build Info
      if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
      run: |
        echo "Sending build information to CodeLogic..."
        docker run --rm \\
          --env CODELOGIC_HOST="${{{{ env.CODELOGIC_HOST }}}}" \\
          --env AGENT_UUID="${{{{ env.AGENT_UUID }}}}" \\
          --env AGENT_PASSWORD="${{{{ env.AGENT_PASSWORD }}}}" \\
          --volume "${{{{ github.workspace }}}}:/scan" \\
          --volume "${{{{ github.workspace }}}}/logs:/log_file_path" \\
          ${{{{ env.CODELOGIC_HOST }}}}/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log" \\
          --job-name="${{{{ github.repository }}}}" \\
          --build-number="${{{{ github.run_number }}}}"
      continue-on-error: true
    
    - name: Upload build logs
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: build-logs
        path: logs/
        retention-days: 30

  notify:
    needs: codelogic-scan
    runs-on: ubuntu-latest
    if: always()
    steps:
    - name: Notify Success
      if: needs.codelogic-scan.result == 'success'
      run: |
        echo "CodeLogic scan completed successfully"
        # Add notification logic here
    
    - name: Notify Failure
      if: needs.codelogic-scan.result == 'failure'
      run: |
        echo "CodeLogic scan failed"
        # Add notification logic here
```

### GitHub Secrets Configuration

Add these secrets to your repository settings:

1. Go to Settings → Secrets and variables → Actions
2. Add the following repository secrets:
   - `CODELOGIC_HOST`: Your CodeLogic server URL
   - `AGENT_UUID`: Your agent UUID
   - `AGENT_PASSWORD`: Your agent password

### GitHub Actions Best Practices

1. **Security**: Use repository secrets for sensitive information
2. **Performance**: Use matrix strategy for multiple agent types
3. **Artifacts**: Upload build logs for debugging
4. **Notifications**: Integrate with Slack/Teams for status updates
5. **Caching**: Use Docker layer caching for faster builds
"""


def generate_azure_devops_pipeline(agent_type, scan_triggers):
    """Generate complete Azure DevOps pipeline"""
    return f"""
### Complete Azure DevOps Pipeline

Create `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include: {scan_triggers}

variables:
  codelogicHost: 'https://your-instance.app.codelogic.com'
  agentUuid: $(codelogicAgentUuid)
  agentPassword: $(codelogicAgentPassword)

stages:
- stage: CodeLogicScan
  displayName: 'CodeLogic Scan'
  jobs:
  - job: Scan
    displayName: 'Run CodeLogic Scan'
    pool:
      vmImage: 'ubuntu-latest'
    
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
          --application "$(Build.DefinitionName)" \\
          --path /scan \\
          --scan-space-name "$(Build.BuildNumber)" \\
          --rescan \\
          --expunge-scan-sessions
      continueOnError: true
      
    - task: Docker@2
      displayName: 'Send Build Info'
      condition: and(succeededOrFailed(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
      inputs:
        command: 'run'
        arguments: |
          --rm \\
          --env CODELOGIC_HOST="$(codelogicHost)" \\
          --env AGENT_UUID="$(agentUuid)" \\
          --env AGENT_PASSWORD="$(agentPassword)" \\
          --volume "$(Build.SourcesDirectory):/scan" \\
          --volume "$(Build.SourcesDirectory)/logs:/log_file_path" \\
          $(codelogicHost)/codelogic_{agent_type}:latest send_build_info \\
          --log-file="/log_file_path/build.log" \\
          --job-name="$(Build.DefinitionName)" \\
          --build-number="$(Build.BuildNumber)"
      continueOnError: true
      
    - task: PublishBuildArtifacts@1
      displayName: 'Publish Build Logs'
      inputs:
        pathToPublish: 'logs'
        artifactName: 'build-logs'
      condition: always()
```

### Azure DevOps Configuration

1. **Variable Groups**:
   - Create a variable group for CodeLogic configuration
   - Add variables: `codelogicAgentUuid`, `codelogicAgentPassword`
   - Mark as secret variables

2. **Service Connections**:
   - Configure Docker registry connections if needed
   - Set up authentication for private registries

3. **Notifications**:
   - Configure email notifications for build failures
   - Set up Slack/Teams integration for status updates
"""


def generate_gitlab_pipeline(agent_type, scan_triggers):
    """Generate complete GitLab CI pipeline"""
    return f"""
### Complete GitLab CI Pipeline

Create `.gitlab-ci.yml`:

```yaml
variables:
  CODELOGIC_HOST: "https://your-instance.app.codelogic.com"
  AGENT_UUID: $AGENT_UUID
  AGENT_PASSWORD: $AGENT_PASSWORD
  DOCKER_DRIVER: overlay2

stages:
  - scan
  - build-info
  - notify

codelogic_scan:
  stage: scan
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker info
    - |
      if [[ "$CI_COMMIT_REF_NAME" =~ ^(main|develop|master)$ ]]; then
        export SCAN_SPACE="YOUR_SCAN_SPACE_NAME-$CI_COMMIT_REF_NAME"
      else
        export SCAN_SPACE="YOUR_SCAN_SPACE_NAME-$CI_COMMIT_REF_NAME-$CI_PIPELINE_ID"
      fi
  script:
    - |
      echo "Starting CodeLogic {agent_type} scan..."
      docker run --pull always --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest analyze \\
        --application "$CI_PROJECT_NAME" \\
        --path /scan \\
        --scan-space-name "$SCAN_SPACE" \\
        --rescan \\
        --expunge-scan-sessions
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^({scan_triggers.join('|')})$/
  allow_failure: true
  artifacts:
    reports:
      junit: logs/scan-results.xml
    paths:
      - logs/
    expire_in: 30 days

send_build_info:
  stage: build-info
  image: docker:latest
  services:
    - docker:dind
  script:
    - |
      echo "Sending build information to CodeLogic..."
      docker run --rm \\
        --env CODELOGIC_HOST="$CODELOGIC_HOST" \\
        --env AGENT_UUID="$AGENT_UUID" \\
        --env AGENT_PASSWORD="$AGENT_PASSWORD" \\
        --volume "$CI_PROJECT_DIR:/scan" \\
        --volume "$CI_PROJECT_DIR/logs:/log_file_path" \\
        $CODELOGIC_HOST/codelogic_{agent_type}:latest send_build_info \\
        --log-file="/log_file_path/build.log" \\
        --job-name="$CI_PROJECT_NAME" \\
        --build-number="$CI_PIPELINE_ID"
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"
  allow_failure: true

notify_success:
  stage: notify
  image: alpine:latest
  script:
    - echo "CodeLogic scan completed successfully"
    # Add notification logic here
  rules:
    - if: $CI_COMMIT_BRANCH == "main" && $codelogic_scan.status == "success"
  when: on_success

notify_failure:
  stage: notify
  image: alpine:latest
  script:
    - echo "CodeLogic scan failed"
    # Add notification logic here
  rules:
    - if: $CI_COMMIT_BRANCH == "main" && $codelogic_scan.status == "failed"
  when: on_failure
```

### GitLab CI Configuration

1. **Variables**:
   - Go to Settings → CI/CD → Variables
   - Add variables: `AGENT_UUID`, `AGENT_PASSWORD`
   - Mark as protected and masked

2. **Docker Configuration**:
   - Ensure Docker-in-Docker is enabled
   - Configure appropriate resource limits

3. **Notifications**:
   - Configure Slack/Teams integration
   - Set up email notifications for failures
"""
