# agent_parser.py
from google import genai
from pydantic import BaseModel, Field

# 1. Define the exact JSON structure we want the AI to return
class ActionIntent(BaseModel):
    action: str = Field(description="The type of action: 'update_database', 'create_record', 'send_email', 'book_flight', or 'buy_groceries'")
    amount: float = Field(default=0.0, description="The total dollar amount, salary, or transaction cost. Default to 0 if not mentioned.")
    target: str = Field(description="The target employee name (e.g., 'Bob Smith', 'Diana Prince'), destination, store, or recipient email.")
    field: str = Field(default="", description="If updating database, the column/field name: 'salary', 'role', 'department', or 'email'.")
    new_value: str = Field(default="", description="If updating database, the new value to write to the column. Otherwise empty.")
    role: str = Field(default="", description="If database operation, the designation/role involved (e.g., 'admin', 'sales_rep', 'engineer', 'executive').")
    subject: str = Field(default="", description="If sending an email, a concise email subject line. Otherwise empty.")
    body: str = Field(default="", description="If sending an email, the complete drafted body text. Otherwise empty.")

def get_candidate_models(client, preferred_model=None):
    """
    Finds available models supporting generateContent for the provided API key,
    prioritizing gemini-3.6-flash, gemini-3.5-flash, and gemini-2.5-flash.
    """
    if preferred_model and preferred_model != "Auto-detect":
        return [preferred_model]

    defaults = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-2.5-flash-lite']
    try:
        available = []
        for m in client.models.list():
            model_id = m.name.replace("models/", "")
            actions = getattr(m, 'supported_actions', []) or []
            if not actions or 'generateContent' in actions:
                available.append(model_id)

        matched = [m for m in defaults if m in available]
        if matched:
            return matched
        flash_models = [m for m in available if 'flash' in m]
        if flash_models:
            return flash_models
        if available:
            return available
    except Exception:
        pass
    return defaults

def parse_user_intent(user_prompt: str, api_key: str, model_name: str = None, *args, **kwargs):
    """
    Sends the user's prompt to Gemini and forces it to return 
    a structured Python dictionary instead of a chat response.
    """
    if model_name is None and args:
        model_name = args[0]
    if model_name is None and "model_name" in kwargs:
        model_name = kwargs["model_name"]
    # Connect to the AI using the key from the Streamlit UI
    client = genai.Client(api_key=api_key)
    
    # Instruct the AI to act as a structured extractor & drafter
    system_instruction = (
        "You are an AI intent extraction engine. "
        "Extract the action ('update_database', 'create_record', 'send_email', 'book_flight', or 'buy_groceries'), "
        "amount (salary or numeric cost), and target (employee name, destination, store, or recipient email). "
        "If a database update or raise is requested, extract the employee name as target, "
        "set field to 'salary' (or other field), new_value to the new value, and amount to the salary number. "
        "If a role/designation is mentioned (e.g., admin, executive, sales_rep), extract it in role. "
        "If the user wants to send an email, draft an appropriate subject and professional body text."
    )
    
    models_to_try = get_candidate_models(client, preferred_model=model_name)
    last_error = None
    
    for candidate in models_to_try:
        try:
            # Make the API Call with a Strict Schema (Pydantic)
            response = client.models.generate_content(
                model=candidate,
                contents=f"{system_instruction}\n\nCommand: {user_prompt}",
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ActionIntent, # Forces the strict format
                    "temperature": 0.1 # Keep it low so the AI doesn't hallucinate
                },
            )
            
            # Return the extracted data as a Python dictionary
            data = response.parsed.model_dump()
            data["_model_used"] = candidate
            return data
        except Exception as e:
            last_error = f"Model '{candidate}' error: {str(e)}"
            continue
            
    return {"error": f"AI Parsing Failed: {str(last_error)}"}

# --- LOCAL TESTING ---
# Dev 2 can run this directly in the terminal to test it
if __name__ == "__main__":
    TEST_API_KEY = "YOUR_GEMINI_API_KEY" 
    
    if TEST_API_KEY != "YOUR_GEMINI_API_KEY":
        print("Testing flight intent...")
        print(parse_user_intent("Buy a ticket to London for $600", TEST_API_KEY))
        print("\nTesting email intent...")
        print(parse_user_intent("Send an email to contact@allowed-vendor.com about the invoice", TEST_API_KEY))
    else:
        print("Add your API key to test locally!")


