# agent_parser.py
from google import genai
from pydantic import BaseModel, Field

# 1. Define the exact JSON structure we want the AI to return
class ActionIntent(BaseModel):
    action: str = Field(description="The type of action, e.g., 'book_flight', 'buy_groceries'")
    amount: float = Field(description="The total cost in dollars. Default to 0 if not mentioned.")
    target: str = Field(description="The destination, store name, or recipient.")

def parse_user_intent(user_prompt: str, api_key: str):
    """
    Sends the user's prompt to Gemini and forces it to return 
    a structured Python dictionary instead of a chat response.
    """
    # Connect to the AI using the key from the Streamlit UI
    client = genai.Client(api_key=api_key)
    
    # Instruct the AI to act purely as a data extractor
    system_instruction = "You are an intent extraction engine. Extract the action, amount, and target from the user's command."
    
    try:
        # Make the API Call with a Strict Schema (Pydantic)
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=f"{system_instruction}\n\nCommand: {user_prompt}",
            config={
                "response_mime_type": "application/json",
                "response_schema": ActionIntent, # Forces the strict format
                "temperature": 0.1 # Keep it low so the AI doesn't hallucinate
            },
        )
        
        # Return the extracted data as a Python dictionary
        # Example output: {"action": "book_flight", "amount": 450.0, "target": "New York"}
        return response.parsed.model_dump()
        
    except Exception as e:
        return {"error": f"AI Parsing Failed: {str(e)}"}

# --- LOCAL TESTING ---
# Dev 2 can run this directly in the terminal to test it
if __name__ == "__main__":
    # Get a free API key from aistudio.google.com and paste it here for testing
    TEST_API_KEY = "YOUR_GEMINI_API_KEY" 
    
    if TEST_API_KEY != "YOUR_GEMINI_API_KEY":
        print("Testing the AI...")
        result = parse_user_intent("Buy a ticket to London for $600", TEST_API_KEY)
        print(result) 
    else:
        print("Add your API key to test locally!")
