"""
Agent using Strands Agents framework with Amazon Bedrock model
"""
from strands import Agent, tool
from strands_tools import calculator, current_time # Import the calculator tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel

# Initialize the BedrockAgentCoreApp
app = BedrockAgentCoreApp()

# # Define calculator tool
# @tool
# def calculator(expression: str) -> float:
#     """
#     Evaluate a mathematical expression safely.
    
#     Args:
#         expression: A mathematical expression as a string (e.g., "2 + 3", "10 * 5", "100 / 4")
    
#     Returns:
#         The result of the mathematical expression
#     """
#     try:
#         # Only allow basic mathematical operations for safety
#         allowed_chars = set('0123456789+-*/.() ')
#         if not all(c in allowed_chars for c in expression):
#             raise ValueError("Expression contains invalid characters")
        
#         # Evaluate the expression safely
#         result = eval(expression)
#         return float(result)
#     except Exception as e:
#         raise ValueError(f"Invalid mathematical expression: {e}")

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
def handle_request(payload):
    """
    Handle incoming requests to the agent
    
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
