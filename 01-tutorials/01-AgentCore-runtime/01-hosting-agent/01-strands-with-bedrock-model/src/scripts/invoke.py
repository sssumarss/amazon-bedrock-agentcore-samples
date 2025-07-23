#!/usr/bin/env python3
"""
Invoke a deployed agent on Amazon Bedrock AgentCore Runtime
"""

import argparse
import json
import boto3
import os

def parse_args():
    parser = argparse.ArgumentParser(description='Invoke a deployed agent on Amazon Bedrock AgentCore Runtime')
    parser.add_argument('--agent-name', type=str, help='Name of the deployed agent (to load from deployment file)')
    parser.add_argument('--agent-arn', type=str, help='ARN of the deployed agent (alternative to --agent-name)')
    parser.add_argument('--region', type=str, default=None, help='AWS region (default: from deployment file or us-east-1)')
    parser.add_argument('--prompt', type=str, required=True, help='Prompt to send to the agent')
    return parser.parse_args()

def load_deployment_info(agent_name):
    """Load deployment information from file"""
    try:
        with open(f"{agent_name}_deployment.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Deployment info file not found: {agent_name}_deployment.json")
        return None

def invoke_agent(agent_arn, prompt, region="us-east-1"):
    """Invoke the agent with a prompt"""
    # Initialize the AgentCore client
    agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
    
    print(f"Invoking agent: {agent_arn}")
    print(f"Prompt: {prompt}")
    
    try:
        # Invoke the agent
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            qualifier='DEFAULT',
            payload=json.dumps({"prompt": prompt})
        )
        
        # Process the response
        print("\nAgent response:")
        print("=" * 50)
        
        if "text/event-stream" in response.get("contentType", ""):
            content = []
            for line in response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        content.append(line)
            result = "\n".join(content)
            print(result)
        else:
            events = []
            for event in response.get("response", []):
                events.append(event)
            result = json.loads(events[0].decode("utf-8"))
            print(result)
        
        print("=" * 50)
        return result
    except Exception as e:
        print(f"Error invoking agent: {e}")
        print("The agent might still be initializing. Please wait a few minutes and try again.")
        return None

def main():
    args = parse_args()
    
    agent_arn = args.agent_arn
    region = args.region or "us-east-1"
    
    # If agent name is provided, load deployment info
    if args.agent_name and not agent_arn:
        deployment_info = load_deployment_info(args.agent_name)
        if deployment_info:
            agent_arn = deployment_info.get("agent_arn")
            region = deployment_info.get("region", region)
    
    if not agent_arn:
        print("Error: Either --agent-name or --agent-arn must be provided")
        return
    
    invoke_agent(agent_arn, args.prompt, region)

if __name__ == "__main__":
    main()
