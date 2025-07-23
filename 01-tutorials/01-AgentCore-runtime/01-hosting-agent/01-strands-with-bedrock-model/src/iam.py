"""
IAM utilities for creating roles and policies for AgentCore Runtime
"""

import boto3
import json
import time
import uuid

def create_agentcore_role(agent_name):
    """
    Create an IAM role for AgentCore Runtime with necessary permissions
    
    Args:
        agent_name (str): Name of the agent
        
    Returns:
        dict: IAM role information
    """
    iam_client = boto3.client('iam')
    role_name = f"{agent_name}_role_{str(uuid.uuid4())[:8]}"
    
    # Create the IAM role with trust relationship for AgentCore
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description=f"Role for AgentCore Runtime {agent_name}"
        )
        
        # Attach necessary policies for Bedrock
        bedrock_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}_bedrock_policy",
            PolicyDocument=json.dumps(bedrock_policy)
        )
        
        # Add ECR permissions
        ecr_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}_ecr_policy",
            PolicyDocument=json.dumps(ecr_policy)
        )
        
        # Wait for role to propagate
        print(f"Created role {role_name}, waiting for it to propagate...")
        time.sleep(10)
        
        return role
    except Exception as e:
        print(f"Error creating role: {e}")
        raise

def cleanup_role(role_name):
    """
    Clean up an IAM role and its policies
    
    Args:
        role_name (str): Name of the role to clean up
    """
    iam_client = boto3.client('iam')
    
    try:
        # List and delete attached policies
        policies = iam_client.list_role_policies(
            RoleName=role_name,
            MaxItems=100
        )
        
        for policy_name in policies['PolicyNames']:
            print(f"Deleting policy: {policy_name}")
            iam_client.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
        
        # Delete the role
        iam_client.delete_role(
            RoleName=role_name
        )
        
        print(f"Deleted role: {role_name}")
    except Exception as e:
        print(f"Error cleaning up role: {e}")
        raise
