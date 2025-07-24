"""
Agent using Strands Agents framework with Amazon Bedrock model
"""
from strands import Agent, tool
from strands_tools import calculator, current_time # Import the calculator, time tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel

# Initialize the BedrockAgentCoreApp
app = BedrockAgentCoreApp()

# Create a custom tool 
@tool
def weather():
    """ Get weather """ # Dummy implementation
    return "sunny"

# Initialize the model and agent
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
model = BedrockModel(model_id=MODEL_ID)

agent = Agent(
    model=model,
    tools=[calculator, current_time, weather],
    system_prompt="You're a helpful assistant. You can do simple math calculation, and tell the weather."
)

@app.entrypoint
def strands_agent_bedrock(payload):
    """
    Invoke the agent with a payload
    
    Args:
        payload (dict): The request payload containing a 'prompt' field
        
    Returns:
        str: The agent's response
    """
    try:
        user_input = payload.get("prompt")
        print(f"Received user input: {user_input}")
        
        response = agent(user_input)
        result = response.message['content'][0]['text']
        
        print(f"Agent response: {result}")
        return result
    except Exception as e:
        import traceback
        print(f"Error processing request: {e}")
        print(traceback.format_exc())
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run()
