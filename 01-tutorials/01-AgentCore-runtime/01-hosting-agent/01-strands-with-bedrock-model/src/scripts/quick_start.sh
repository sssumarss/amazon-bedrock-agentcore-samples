#!/bin/bash
# Quick start script for deploying and testing the math agent

set -e  # Exit on error

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker and try again."
  exit 1
fi

# Check for AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
  echo "Error: AWS credentials not found or invalid. Please configure your AWS credentials."
  exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r "$PROJECT_ROOT/requirements.txt"

# Deploy the agent
echo "Deploying the agent..."
python "$SCRIPT_DIR/deploy.py" --agent-name agentcore_strands

# Test the agent with a few examples
echo ""
echo "Testing the agent with a few examples..."
python "$SCRIPT_DIR/invoke.py" --agent-name agentcore_strands --prompt "How is the weather?"
python "$SCRIPT_DIR/invoke.py" --agent-name agentcore_strands --prompt "What is 100 - 35?"
python "$SCRIPT_DIR/invoke.py" --agent-name agentcore_strands --prompt "What is 12 * 8?"
python "$SCRIPT_DIR/invoke.py" --agent-name agentcore_strands --prompt "What is 144 / 12?"

echo ""
echo "Agent is deployed and ready to use!"
echo "To invoke the agent with your own prompts, run:"
echo "  python src/scripts/invoke.py --agent-name agentcore_strands --prompt \"Your question here\""
echo ""
echo "To clean up resources when done, run:"
echo "  python src/scripts/deploy.py --agent-name agentcore_strands --cleanup-only"
