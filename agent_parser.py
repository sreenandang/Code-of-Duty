# agent_parser.py
from google import genai
from pydantic import BaseModel, Field

# 1. Define the exact JSON structure we want the AI to return
class ActionIntent(BaseModel):
    action: str = Field(description="The type of action: 'update_database', 'create_record', 'send_email', 'book_flight', 'buy_groceries', or 'redact_data'")
    amount: float = Field(default=0.0, description="The total dollar amount, salary, or transaction cost. Default to 0 if not mentioned.")
    target: str = Field(default="", description="The target employee name (e.g., 'Bob Smith'), destination, store, recipient email, or target file path.")
    field: str = Field(default="", description="If updating database, the column/field name: 'salary', 'role', 'department', or 'email'.")
    new_value: str = Field(default="", description="If updating database, the new value to write to the column. Otherwise empty.")
    role: str = Field(default="", description="If database operation, the designation/role involved (e.g., 'admin', 'sales_rep', 'engineer', 'executive').")
    subject: str = Field(default="", description="If sending an email, a concise email subject line. Otherwise empty.")
    body: str = Field(default="", description="If sending an email, the complete drafted body text. Otherwise empty.")
    destination_path: str = Field(default="", description="If redacting or saving a file, the exact destination file path on disk (e.g., './workspace/public_logs/cleaned_support_log.txt').")
    redacted_content: str = Field(default="", description="If redacting data, the full cleaned text with all sensitive data (passwords, phone numbers, addresses, SSNs, API keys) masked as [REDACTED_TYPE].")

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
        "Extract the action ('update_database', 'create_record', 'send_email', 'book_flight', 'buy_groceries', or 'redact_data'), "
        "amount (salary or numeric cost), and target (employee name, destination, store, recipient email, or target file path). "
        "1. DATABASE ACTIONS: If a database update or raise is requested, extract employee name as target, "
        "set field to 'salary' (or other field), new_value to new value, and amount to salary number. "
        "If a new employee row is being created, use 'create_record'. "
        "If a role/designation is mentioned (e.g., admin, executive, sales_rep), extract it in role. "
        "2. EMAIL ACTIONS: If the user wants to send an email, set action to 'send_email', draft subject and body text. "
        "3. FILE SANDBOX & REDACTION ACTIONS: If the user asks to create, write, save, redact, or sanitize a file "
        "(e.g., 'create a gedit text file', 'write a text file', 'save hello world to file', or 'redact sensitive data in file'): "
        "always set action to 'redact_data'. "
        "Extract or construct the full destination file path into destination_path and target. "
        "For example, if the prompt mentions 'inside public logs inside workspace' or 'in public logs', "
        "resolve the path to './workspace/public_logs/hello_world.txt' (or the specified file name). "
        "Put the file text content (e.g. 'hello world' or the redacted text with sensitive data masked as [REDACTED_TYPE]) into redacted_content."
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


