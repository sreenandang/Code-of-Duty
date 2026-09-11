# token_engine.py
from pymacaroons import Macaroon, Verifier

# In a real app, this key is locked in a vault. 
# For a hackathon, we hardcode it here.
SECRET_KEY = "my-super-secret-hackathon-key"
IDENTIFIER = "demo-session-id"
LOCATION = "familyguard-gateway"

def create_grant(agent_id, max_spend, allowed_action):
    """
    Step 1: The Human creates a Macaroon with base rules.
    """
    # Create the blank token
    m = Macaroon(location=LOCATION, identifier=IDENTIFIER, key=SECRET_KEY)
    
    # Add the rules (these are cryptographically baked in)
    m.add_first_party_caveat(f"agent_id = {agent_id}")
    m.add_first_party_caveat(f"action = {allowed_action}")
    m.add_first_party_caveat(f"max_spend = {max_spend}")
    
    # Serialize returns a long encrypted string we can pass around
    return m.serialize()

def attenuate_grant(token_string, stricter_max_spend):
    """
    Step 2: Attenuation. (The Matryoshka Doll of Rules)
    An agent can pass a token to a sub-agent, but can only LOWER the budget.
    """
    m = Macaroon.deserialize(token_string)
    
    # We add another caveat. Macaroons mandate that ALL caveats must be true.
    # Therefore, adding a stricter rule securely overrides the looser one.
    m.add_first_party_caveat(f"max_spend = {stricter_max_spend}")
    
    return m.serialize()

def verify_action(token_string, requested_agent, requested_action, requested_amount):
    """
    Step 3: The Gateway checks if the action breaks any rules in the token.
    """
    try:
        m = Macaroon.deserialize(token_string)
        v = Verifier()
        
        # 1. Check exact string matches
        v.satisfy_exact(f"agent_id = {requested_agent}")
        v.satisfy_exact(f"action = {requested_action}")
        
        # 2. Check the dynamic math logic
        # This function runs against every "max_spend" caveat in the token
        def check_spend(predicate):
            if predicate.startswith("max_spend = "):
                limit = float(predicate.split(" = ")[1])
                # Ensure the AI is asking for less than or equal to the limit
                return requested_amount <= limit
            return False
            
        v.satisfy_general(check_spend)
        
        # 3. The Moment of Truth: Cryptographically verify the token hasn't been tampered with
        v.verify(m, SECRET_KEY)
        return True, "✅ Approved: Cryptographic verification passed."
        
    except Exception as e:
        # If ANY rule fails, or if a hacker altered the token string, it fails.
        return False, f"🛑 Blocked: {str(e)}"

# --- LOCAL TESTING ENVIRONMENT ---
# If Dev 1 runs `python token_engine.py` in the terminal, this block will execute
# and prove the logic works before we ever attach it to a UI.
if __name__ == "__main__":
    print("--- 1. MINTING HUMAN TOKEN ---")
    token = create_grant("TravelBot", 400.0, "book_flight")
    print(f"Token string created (First 40 chars): {token[:40]}...\n")
    
    print("--- 2. VERIFYING GOOD ACTION ---")
    # AI tries to spend $350 on a flight
    is_valid, msg = verify_action(token, "TravelBot", "book_flight", 350.0)
    print(msg) 
    
    print("\n--- 3. VERIFYING HACKER ACTION (SCOPE CREEP) ---")
    # Hacker intercepts token and tries to spend $500
    is_valid, msg = verify_action(token, "TravelBot", "book_flight", 500.0)
    print(msg)
