#!/usr/bin/env python3
"""
Test the agent locally before deployment
"""

import argparse
import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def parse_args():
    parser = argparse.ArgumentParser(description='Test the agent locally')
    parser.add_argument('--prompt', type=str, default='What is the weather?',
                        help='Prompt to send to the agent (default: "What is the weather?")')
    return parser.parse_args()

def main():
    args = parse_args()
    
    try:
        # Import the agent module
        from src.agent import agent
        
        print(f"Testing agent with prompt: '{args.prompt}'")
        response = agent(args.prompt)
        
        print("\nAgent response:")
        print("=" * 50)
        print(response.message['content'][0]['text'])
        print("=" * 50)
    except Exception as e:
        import traceback
        print(f"Error testing agent: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
