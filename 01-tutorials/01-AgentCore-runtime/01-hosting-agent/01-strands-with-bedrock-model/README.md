# Hosting Strands Agents with Amazon Bedrock models in Amazon Bedrock AgentCore Runtime

## Overview

In this tutorial we will learn how to host your existing agent, using Amazon Bedrock AgentCore Runtime. 

We will focus on a Strands Agents with Amazon Bedrock model example. For LangGraph with Amazon Bedrock model check [here](../02-langgraph-with-bedrock-model)
and for a Strands Agents with an OpenAI model check [here](../03-strands-with-openai-model).


### Tutorial Details

| Information         | Details                                                                          |
|:--------------------|:---------------------------------------------------------------------------------|
| Tutorial type       | Conversational                                                                   |
| Agent type          | Single                                                                           |
| Agentic Framework   | Strands Agents                                                                   |
| LLM model           | Anthropic Claude Sonnet 4                                                        |
| Tutorial components | Hosting agent on AgentCore Runtime. Using Strands Agent and Amazon Bedrock Model |
| Tutorial vertical   | Cross-vertical                                                                   |
| Example complexity  | Easy                                                                             |
| SDK used            | Amazon BedrockAgentCore Python SDK and boto3                                     |

### Tutorial Architecture

In this tutorial we will describe how to deploy an existing agent to AgentCore runtime. 

For demonstration purposes, we will  use a Strands Agent using Amazon Bedrock models

In our example we will use a very simple agent with two tools: `get_weather` and `calculator`. 

<div style="text-align:left">
    <img src="images/architecture_runtime.png" width="100%"/>
</div>

### Tutorial Key Features

* Hosting Agents on Amazon Bedrock AgentCore Runtime
* Using Amazon Bedrock models
* Using Strands Agents

This project demonstrates how to build and deploy an agent using Strands Agents framework with Amazon Bedrock models, and host it on Amazon Bedrock AgentCore Runtime.

You can run this tutorial in two ways:
- **Section 1**: Using Jupyter Notebook for interactive exploration
- **Section 2**: Using Python scripts for direct deployment and testing

## Overview

The agent can perform basic calculation, and tell the weather and is deployed as a containerized service on Amazon Bedrock AgentCore Runtime.

## Project Structure

```
.
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── src/
│   ├── agent.py        # Agent implementation
│   ├── iam.py          # IAM utilities
│   └── scripts/
│       ├── deploy.py       # Deployment script
│       ├── invoke.py       # Invocation script
│       ├── quick_start.sh  # Quick start script for deployment and testing
│       └── test_local.py   # Local testing script
```

## Prerequisites

- Python 3.10+
- AWS account with access to Amazon Bedrock
- Docker installed and running
- AWS CLI configured with appropriate permissions
- Amazon Bedrock AgentCore SDK
- Strands Agents

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure Docker is running on your system.

---

## Section 1: Using Jupyter Notebook

For an interactive exploration of the agent deployment process, you can use the provided Jupyter notebook.

### Running the Notebook

1. Start Jupyter Lab or Jupyter Notebook:

```bash
jupyter lab
# or
jupyter notebook
```

2. Open the notebook file:
   - `runtime_with_strands_and_bedrock_models.ipynb`

3. Follow the step-by-step instructions in the notebook to:
   - Set up the agent configuration
   - Create IAM roles and permissions
   - Deploy the agent to AgentCore Runtime
   - Test the agent with various prompts
   - Clean up resources

The notebook provides detailed explanations and allows you to run code cells interactively to understand each step of the deployment process.

---

## Section 2: Using Python Scripts

For direct deployment and testing using command-line scripts, follow the instructions below.

## Quick Start

For a quick deployment and test of the agent, you can use the provided quick start script:

```bash
./src/scripts/quick_start.sh
```

This script will:
1. Check if Docker is running and AWS credentials are configured
2. Install required dependencies
3. Deploy the agent to AgentCore Runtime
4. Test the agent with several example operations
5. Provide instructions for further use and cleanup

## Deployment

To deploy the agent to Amazon Bedrock AgentCore Runtime:

```bash
python src/scripts/deploy.py
```

This will:
1. Create an IAM role with necessary permissions
2. Configure the AgentCore Runtime
3. Build and push a Docker image to Amazon ECR
4. Deploy the agent to AgentCore Runtime
5. Test the agent with a sample prompt
6. Save deployment information to a JSON file

### Deployment Options

```
usage: deploy.py [-h] [--agent-name AGENT_NAME] [--region REGION]
                [--requirements-file REQUIREMENTS_FILE]
                [--entrypoint ENTRYPOINT] [--test-prompt TEST_PROMPT]
                [--cleanup] [--cleanup-only]

Deploy a Strands Agent to Amazon Bedrock AgentCore Runtime

options:
  -h, --help            show this help message and exit
  --agent-name AGENT_NAME
                        Name for the agent (default: agentcore_strands)
  --region REGION       AWS region (default: from AWS config)
  --requirements-file REQUIREMENTS_FILE
                        Path to requirements.txt file (default: requirements.txt)
  --entrypoint ENTRYPOINT
                        Path to agent entrypoint file (default: src/agent.py)
  --test-prompt TEST_PROMPT
                        Test prompt to invoke the agent after deployment (default: "What is 15 + 27?")
  --cleanup             Clean up resources after testing
  --cleanup-only        Only clean up resources for the specified agent name
```

## Testing Locally

Before deployment, you can test the agent locally:

```bash
python src/scripts/test_local.py --prompt "What is 42 * 7?"
```

## Invoking the Agent

After deployment, you can invoke the agent using the provided script:

```bash
# Using the agent name (loads deployment info from file)
python src/scripts/invoke.py --agent-name agentcore_strands --prompt "What is 42 * 7?"

# Or using the agent ARN directly
python src/scripts/invoke.py --agent-arn <AGENT_ARN> --region <REGION> --prompt "What is the time New York?"
```

### Invocation Options

```
usage: invoke.py [-h] [--agent-name AGENT_NAME] [--agent-arn AGENT_ARN]
                [--region REGION] --prompt PROMPT

Invoke a deployed agent on Amazon Bedrock AgentCore Runtime

options:
  -h, --help            show this help message and exit
  --agent-name AGENT_NAME
                        Name of the deployed agent (to load from deployment file)
  --agent-arn AGENT_ARN
                        ARN of the deployed agent (alternative to --agent-name)
  --region REGION       AWS region (default: from deployment file or us-east-1)
  --prompt PROMPT       Prompt to send to the agent
```

## Cleanup

To clean up all resources created during deployment:

```bash
# Clean up using deployment information file
python src/scripts/deploy.py --agent-name agentcore_strands --cleanup-only
```

## Implementation Details

The agent is implemented using:
- Strands Agents framework for the agent logic
- Amazon Bedrock Claude Sonnet 4 model for natural language understanding
- Amazon Bedrock AgentCore Runtime for hosting
- Docker for containerization


