import streamlit as st
from token_engine import create_grant, verify_action
from agent_parser import parse_user_intent

# Configure the visual layout of the web app
st.set_page_config(page_title="AgentAuth Sandbox", layout="wide")

st.title("🛡️ AgentAuth: Zero-Trust AI Delegation")
st.markdown("A demonstration of cryptographic scoped-permissions for autonomous AI agents.")

# Streamlit reruns the script on every click. 
# We use session_state to save the token and logs permanently in the background.
if "current_token" not in st.session_state:
    st.session_state.current_token = None
if "logs" not in st.session_state:
    st.session_state.logs = []

# Create 3 interactive tabs for the judges to click through
tab1, tab2, tab3 = st.tabs(["🧍 1. Human Dashboard", "🤖 2. Agent Sandbox", "📋 3. Security Gateway"])

# --- TAB 1: THE HUMAN ---
with tab1:
    st.header("Mint a Delegation Token")
    st.write("Grant the AI specific permissions. This creates a cryptographically signed Macaroon.")
    
    agent_id = st.text_input("Agent Name", value="TravelBot")
    allowed_action = st.selectbox("Allowed Action", ["book_flight", "buy_groceries", "send_email"])
    max_spend = st.slider("Max Budget ($)", 0, 1000, 400)
    
    if st.button("Mint Cryptographic Token"):
        # Call Dev 1's code!
        token = create_grant(agent_id, max_spend, allowed_action)
        st.session_state.current_token = token
        st.success("Token Minted Successfully!")
        st.code(token[:80] + "... (truncated for display)", language="text")

# --- TAB 2: THE AI AGENT ---
with tab2:
    st.header("Execute AI Action")
    st.write("Type a natural language command. The AI will parse it and attach your token to the request.")
    
    api_key = st.text_input("Your Gemini API Key (Needed for parsing)", type="password")
    user_prompt = st.text_area("Command for AI", value="Book me a flight to New York for $350")
    
    if st.button("Run AI Agent"):
        if not st.session_state.current_token:
            st.error("Wait! You need to mint a token in the Human Dashboard first.")
        elif not api_key:
            st.warning("Please enter your Gemini API Key.")
        else:
            with st.spinner("AI is thinking..."):
                # Call Dev 2's code!
                intent = parse_user_intent(user_prompt, api_key)
                st.info(f"**AI Intent Extracted:** {intent}")
                
                if "error" in intent:
                    st.error(intent["error"])
                else:
                    # Call Dev 1's Verification Gateway!
                    is_valid, msg = verify_action(
                        st.session_state.current_token, 
                        "TravelBot", 
                        intent.get("action"), 
                        intent.get("amount", 0)
                    )
                    
                    # Save it to the audit log
                    st.session_state.logs.append({"prompt": user_prompt, "intent": intent, "result": msg})
                    
                    # Display the final verdict
                    if is_valid:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)

# --- TAB 3: THE AUDIT LOG ---
with tab3:
    st.header("Cryptographic Audit Log")
    st.write("An immutable record of every action the AI attempted, backed by math.")
    
    # Display logs in reverse order (newest first)
    for log in reversed(st.session_state.logs):
        if "Approved" in log["result"]:
            st.success(f"**Action:** {log['intent']} | **Verdict:** {log['result']}")
        else:
            st.error(f"**Action:** {log['intent']} | **Verdict:** {log['result']}")
