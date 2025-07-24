#!/usr/bin/env python3
"""
Deploy a Strands Agent to Amazon Bedrock AgentCore Runtime
"""

import argparse
import json
import time
import boto3
from boto3.session import Session
import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Add the utils directory to the path
utils_path = "/Users/sssumar/Documents/Development/agents/my-agentcore/amazon-bedrock-agentcore-samples/01-tutorials"
sys.path.append(utils_path)

try:
    from bedrock_agentcore_starter_toolkit import Runtime
    from utils import create_agentcore_role, cleanup_role
except ImportError:
    print("Required packages not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", 
                          os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "requirements.txt")])
    from bedrock_agentcore_starter_toolkit import Runtime
    from utils import create_agentcore_role, cleanup_role

def parse_args():
    parser = argparse.ArgumentParser(description='Deploy a Strands Agent to Amazon Bedrock AgentCore Runtime')
    parser.add_argument('--agent-name', type=str, default='agentcore_strands',
                        help='Name for the agent (default: agentcore_strands)')
    parser.add_argument('--region', type=str, default=None,
                        help='AWS region (default: from AWS config)')
    parser.add_argument('--requirements-file', type=str, default='requirements.txt',
                        help='Path to requirements.txt file (default: requirements.txt)')
    parser.add_argument('--entrypoint', type=str, default='src/agent.py',
                        help='Path to agent entrypoint file (default: src/agent.py)')
    parser.add_argument('--test-prompt', type=str, default='What is 15 + 27?',
                        help='Test prompt to invoke the agent after deployment (default: "What is 15 + 27?")')
    parser.add_argument('--cleanup', action='store_true',
                        help='Clean up resources after testing')
    parser.add_argument('--cleanup-only', action='store_true',
                        help='Only clean up resources for the specified agent name')
    return parser.parse_args()

def deploy_agent(args):
    """Deploy the agent to AgentCore Runtime"""
    # Get AWS region
    boto_session = Session()
    region = args.region or boto_session.region_name
    print(f"Using AWS region: {region}")
    
    # Create IAM role for AgentCore Runtime
    print(f"Creating IAM role for agent: {args.agent_name}")
    agentcore_iam_role = create_agentcore_role(agent_name=args.agent_name)
    print(f"Created IAM role: {agentcore_iam_role['Role']['Arn']}")
    
    # Configure AgentCore Runtime
    print("Configuring AgentCore Runtime...")
    agentcore_runtime = Runtime()
    response = agentcore_runtime.configure(
        entrypoint=args.entrypoint,
        execution_role=agentcore_iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file=args.requirements_file,
        region=region,
        agent_name=args.agent_name
    )
    print("Configuration complete.")
    
    # Launch agent to AgentCore Runtime
    print("Launching agent to AgentCore Runtime...")
    launch_result = agentcore_runtime.launch()
    print(f"Agent launched with ID: {launch_result.agent_id}")
    print(f"Agent ARN: {launch_result.agent_arn}")
    print(f"ECR URI: {launch_result.ecr_uri}")
    
    # Check deployment status
    print("Checking deployment status...")
    status_response = agentcore_runtime.status()
    status = status_response.endpoint['status']
    end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    
    while status not in end_status:
        print(f"Current status: {status}. Waiting...")
        time.sleep(10)
        status_response = agentcore_runtime.status()
        status = status_response.endpoint['status']
    
    print(f"Final deployment status: {status}")
    
    if status == 'READY':
        # Test the deployed agent
        print(f"Testing agent with prompt: '{args.test_prompt}'")
        invoke_response = agentcore_runtime.invoke({"prompt": args.test_prompt})
        
        # Process and display response
        response_text = json.loads(invoke_response['response'][0].decode("utf-8"))
        print("\nAgent response:")
        print("=" * 50)
        print(response_text)
        print("=" * 50)
        
        # Show how to invoke with boto3
        print("\nYou can also invoke the agent using boto3:")
        print(f"""
import boto3
import json

agentcore_client = boto3.client('bedrock-agentcore', region_name='{region}')
response = agentcore_client.invoke_agent_runtime(
    agentRuntimeArn='{launch_result.agent_arn}',
    qualifier='DEFAULT',
    payload=json.dumps({{"prompt": "Your question here"}})
)

# Process the response
if "text/event-stream" in response.get("contentType", ""):
    content = []
    for line in response["response"].iter_lines(chunk_size=1):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                content.append(line)
    print("\\n".join(content))
else:
    events = []
    for event in response.get("response", []):
        events.append(event)
    print(json.loads(events[0].decode("utf-8")))
""")
        
        # Save deployment info to a file for later use
        deployment_info = {
            "agent_id": launch_result.agent_id,
            "agent_arn": launch_result.agent_arn,
            "ecr_uri": launch_result.ecr_uri,
            "role_name": agentcore_iam_role['Role']['RoleName'],
            "region": region
        }
        
        with open(f"{args.agent_name}_deployment.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"\nDeployment information saved to {args.agent_name}_deployment.json")
        
        # Cleanup if requested
        if args.cleanup:
            cleanup_resources(deployment_info)
            
        return deployment_info
    else:
        print(f"Deployment failed with status: {status}")
        print("Check AWS CloudWatch logs for more details.")
        return None

def cleanup_resources(deployment_info):
    """Clean up resources created during deployment"""
    print("\nCleaning up resources...")
    
    # Initialize clients
    region = deployment_info.get("region", "us-east-1")
    agentcore_control_client = boto3.client('bedrock-agentcore-control', region_name=region)
    ecr_client = boto3.client('ecr', region_name=region)
    
    # Delete agent runtime
    agent_id = deployment_info.get("agent_id")
    if agent_id:
        print(f"Deleting agent runtime: {agent_id}")
        try:
            agentcore_control_client.delete_agent_runtime(
                agentRuntimeId=agent_id
            )
        except Exception as e:
            print(f"Error deleting agent runtime: {e}")
    
    # Delete ECR repository
    ecr_uri = deployment_info.get("ecr_uri")
    if ecr_uri:
        try:
            repo_name = ecr_uri.split('/')[1]
            print(f"Deleting ECR repository: {repo_name}")
            ecr_client.delete_repository(
                repositoryName=repo_name,
                force=True
            )
        except Exception as e:
            print(f"Error deleting ECR repository: {e}")
    
    # Delete IAM role and policies
    role_name = deployment_info.get("role_name")
    if role_name:
        print(f"Deleting IAM role: {role_name}")
        try:
            cleanup_role(role_name)
        except Exception as e:
            print(f"Error deleting IAM role: {e}")
    
    print("Cleanup complete.")

def cleanup_agent(agent_name, region=None):
    """Clean up resources for a specific agent"""
    try:
        # Try to load deployment info from file
        with open(f"{agent_name}_deployment.json", "r") as f:
            deployment_info = json.load(f)
        
        cleanup_resources(deployment_info)
        
        # Remove the deployment info file
        os.remove(f"{agent_name}_deployment.json")
        print(f"Removed deployment info file: {agent_name}_deployment.json")
    except FileNotFoundError:
        print(f"Deployment info file not found: {agent_name}_deployment.json")
        print("Cannot clean up resources without deployment information.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def main():
    args = parse_args()
    
    if args.cleanup_only:
        cleanup_agent(args.agent_name, args.region)
    else:
        deploy_agent(args)

if __name__ == "__main__":
    main()
