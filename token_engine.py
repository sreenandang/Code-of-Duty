# token_engine.py
import os
import smtplib
import uuid
import datetime
from email.message import EmailMessage
from pymacaroons import Macaroon, Verifier

# In a real app, this key is locked in a vault. 
# For a hackathon, we hardcode it here.
SECRET_KEY = "my-super-secret-hackathon-key"
IDENTIFIER = "demo-session-id"
LOCATION = "familyguard-gateway"

import sqlite3

DB_PATH = "company.db"

def init_database():
    """Initializes the company SQLite database with sample employee records."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            salary REAL NOT NULL,
            email TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        sample_employees = [
            ("Alice Johnson", "engineer", "Engineering", 95000.0, "alice@company.local"),
            ("Bob Smith", "sales_rep", "Sales", 65000.0, "bob@company.local"),
            ("Charlie Brown", "marketing", "Marketing", 70000.0, "charlie@company.local"),
            ("Diana Prince", "admin", "IT & Security", 150000.0, "diana.admin@company.local"),
            ("Eve Vance", "executive", "Executive Board", 220000.0, "eve.exec@company.local")
        ]
        cursor.executemany(
            "INSERT INTO employees (name, role, department, salary, email) VALUES (?, ?, ?, ?, ?)",
            sample_employees
        )
        conn.commit()
    conn.close()

def reset_database():
    """Wipes and resets the employee database to default benchmark state."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS employees")
    conn.commit()
    conn.close()
    init_database()

def get_all_employees():
    """Fetches all employee rows as a list of dicts."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, role, department, salary, email FROM employees ORDER BY id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_employee(name):
    """Finds an employee by name (case-insensitive substring or exact match)."""
    if not name:
        return None
    init_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    clean_name = name.strip()
    cursor.execute("SELECT * FROM employees WHERE LOWER(name) = LOWER(?)", (clean_name,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM employees WHERE LOWER(name) LIKE LOWER(?)", (f"%{clean_name}%",))
        row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def execute_db_update(employee_name, field, new_value):
    """Executes an authorized update on an employee record in company.db."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_name = employee_name.strip()
    
    valid_fields = {
        "salary": "salary",
        "role": "role",
        "department": "department",
        "email": "email"
    }
    field_lower = field.strip().lower() if field else "salary"
    column = valid_fields.get(field_lower, "salary")
    
    if column == "salary":
        val = float(new_value)
    else:
        val = str(new_value)
        
    cursor.execute(f"UPDATE employees SET {column} = ? WHERE LOWER(name) LIKE LOWER(?)", (val, f"%{clean_name}%"))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0, f"Updated '{clean_name}' {column} to {val} in company.db"

def execute_db_insert(name, role, department="General", salary=60000.0, email=None):
    """Inserts an authorized new employee record in company.db."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    mail = email or f"{name.lower().replace(' ', '.')}@company.local"
    cursor.execute(
        "INSERT INTO employees (name, role, department, salary, email) VALUES (?, ?, ?, ?, ?)",
        (name.strip(), role.strip().lower(), department.strip(), float(salary), mail)
    )
    conn.commit()
    conn.close()
    return True, f"Inserted employee '{name}' ({role}) with salary ${salary} into company.db"

WORKSPACE_PUBLIC = "./workspace/public_logs"
WORKSPACE_SYS = "./workspace/sys_admin_keys"

def init_workspace():
    """Initializes sample workspace directories and files for testing redaction."""
    os.makedirs(WORKSPACE_PUBLIC, exist_ok=True)
    os.makedirs(WORKSPACE_SYS, exist_ok=True)
    
    sample_raw = """[SUPPORT TICKET #4092]
Customer: Alice Walker
Phone: (555) 234-5678
Address: 742 Evergreen Terrace, Springfield
SSN: 987-65-4321
Temporary Password: Password123!
API Key: sk-live-9948271038592019
Notes: Customer requested assistance with password reset."""

    raw_path = os.path.join(WORKSPACE_PUBLIC, "raw_support_log.txt")
    if not os.path.exists(raw_path):
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(sample_raw)
            
    vault_path = os.path.join(WORKSPACE_SYS, "master_vault.key")
    if not os.path.exists(vault_path):
        with open(vault_path, "w", encoding="utf-8") as f:
            f.write("CONFIDENTIAL_ROOT_PRIVATE_KEY_DO_NOT_DISCLOSE")

def get_workspace_files():
    """Returns a dictionary of files currently saved in the workspace directories."""
    init_workspace()
    result = {"public_logs": [], "sys_admin_keys": []}
    if os.path.exists(WORKSPACE_PUBLIC):
        for f in sorted(os.listdir(WORKSPACE_PUBLIC)):
            path = os.path.join(WORKSPACE_PUBLIC, f)
            if os.path.isfile(path):
                result["public_logs"].append({"name": f, "path": path, "size": os.path.getsize(path)})
    if os.path.exists(WORKSPACE_SYS):
        for f in sorted(os.listdir(WORKSPACE_SYS)):
            path = os.path.join(WORKSPACE_SYS, f)
            if os.path.isfile(path):
                result["sys_admin_keys"].append({"name": f, "path": path, "size": os.path.getsize(path)})
    return result

def execute_file_redaction(destination_path, content):
    """Saves redacted/cleaned content to an authorized disk location."""
    init_workspace()
    clean_path = os.path.normpath(destination_path)
    os.makedirs(os.path.dirname(clean_path) or ".", exist_ok=True)
    with open(clean_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True, f"Cleaned & redacted file written to '{clean_path}' ({len(content)} bytes)"

def create_grant(
    agent_id, 
    max_spend=None, 
    allowed_action="update_database", 
    allowed_domain=None, 
    blocked_domain=None, 
    blocked_roles=None,
    allowed_path_prefix=None,
    blocked_path=None
):
    """
    Step 1: The Human creates a Macaroon with base rules.
    Supports monetary limits, recipient domain blacklists, database role restrictions, and file path sandboxing.
    """
    m = Macaroon(location=LOCATION, identifier=IDENTIFIER, key=SECRET_KEY)
    
    m.add_first_party_caveat(f"agent_id = {agent_id}")
    m.add_first_party_caveat(f"action = {allowed_action}")
    
    # Spend limit or salary ceiling caveat
    if max_spend is not None and (allowed_action not in ["send_email", "redact_data"] or max_spend > 0):
        m.add_first_party_caveat(f"max_spend = {max_spend}")
        
    # Database Row-Level Security: Disallow editing or accessing rows with protected designations
    if blocked_roles:
        for r in str(blocked_roles).split(","):
            r_val = r.strip().lower()
            if r_val:
                m.add_first_party_caveat(f"disallowed_role = {r_val}")

    # File Sandbox: Path prefix confinement
    if allowed_path_prefix:
        m.add_first_party_caveat(f"allowed_path_prefix = {allowed_path_prefix.strip()}")
        
    # File Sandbox: Forbidden directory / path segment
    if blocked_path:
        for item in str(blocked_path).split(","):
            p_val = item.strip()
            if p_val:
                m.add_first_party_caveat(f"disallowed_path = {p_val}")

    # Blacklist domain caveat (for email)
    if blocked_domain:
        for item in str(blocked_domain).split(","):
            dom_val = item.strip().lower()
            if dom_val:
                if not dom_val.startswith("@"):
                    dom_val = f"@{dom_val}"
                m.add_first_party_caveat(f"disallowed_domain = {dom_val}")

    # Whitelist domain caveat (for email)
    if allowed_domain:
        domain_val = allowed_domain.strip().lower()
        if not domain_val.startswith("@"):
            domain_val = f"@{domain_val}"
        m.add_first_party_caveat(f"allowed_domain = {domain_val}")
    
    return m.serialize()

def inspect_token(token_string):
    """Unpacks and returns the cryptographic caveats inside a token."""
    try:
        m = Macaroon.deserialize(token_string)
        return [c.caveat_id for c in m.caveats]
    except Exception:
        return []

def attenuate_grant(
    token_string, 
    stricter_max_spend=None, 
    add_blocked_roles=None, 
    add_blocked_domain=None, 
    stricter_domain=None,
    add_blocked_path=None
):
    """
    Step 2: Attenuation. (The Matryoshka Doll of Rules)
    An agent can pass a token to a sub-agent, but can only LOWER permissions.
    """
    m = Macaroon.deserialize(token_string)
    
    if stricter_max_spend is not None:
        m.add_first_party_caveat(f"max_spend = {stricter_max_spend}")
    if add_blocked_roles is not None:
        for r in str(add_blocked_roles).split(","):
            r_val = r.strip().lower()
            if r_val:
                m.add_first_party_caveat(f"disallowed_role = {r_val}")
    if add_blocked_path is not None:
        for item in str(add_blocked_path).split(","):
            p_val = item.strip()
            if p_val:
                m.add_first_party_caveat(f"disallowed_path = {p_val}")
    if add_blocked_domain is not None:
        for item in str(add_blocked_domain).split(","):
            dom = item.strip().lower()
            if dom:
                if not dom.startswith("@"):
                    dom = f"@{dom}"
                m.add_first_party_caveat(f"disallowed_domain = {dom}")
    if stricter_domain is not None:
        dom = stricter_domain.strip().lower()
        if not dom.startswith("@"):
            dom = f"@{dom}"
        m.add_first_party_caveat(f"allowed_domain = {dom}")
    
    return m.serialize()

def normalize_target_path(target_path):
    """Normalizes target path and handles relative public_logs/sys_admin_keys paths."""
    if not target_path:
        return ""
    clean = str(target_path).strip().strip("'\"")
    norm = os.path.normpath(clean)
    if not norm.startswith("workspace/") and not norm.startswith("./workspace/"):
        if norm.startswith("public_logs") or norm.startswith("sys_admin_keys"):
            norm = os.path.normpath(os.path.join("workspace", norm))
        elif norm.startswith("/public_logs") or norm.startswith("/sys_admin_keys"):
            norm = os.path.normpath(os.path.join("workspace", norm.lstrip("/")))
    return norm

def diagnose_rule_violation(
    token_string, 
    requested_agent, 
    requested_action, 
    requested_amount=0, 
    requested_recipient=None, 
    target_name=None, 
    requested_role=None, 
    target_path=None
):
    """Provides a clear, user-friendly diagnostic explaining the exact caveat that was violated."""
    try:
        m = Macaroon.deserialize(token_string)
    except Exception:
        return "Invalid or corrupted token structure."

    clean_path = normalize_target_path(target_path)
    target_record = get_employee(target_name) if target_name else None
    current_role = target_record["role"].lower() if target_record else None

    for c in m.caveats:
        cid = c.caveat_id
        if cid.startswith("agent_id = "):
            exp = cid.split(" = ")[1].strip()
            if requested_agent != exp:
                return f"Agent ID mismatch: Token was minted for agent '{exp}', but requested by '{requested_agent}'."
        elif cid.startswith("action = "):
            exp = cid.split(" = ")[1].strip()
            if requested_action != exp:
                return f"Action mismatch: Active token only authorizes '{exp}', but AI attempted '{requested_action}'. (Please mint a new token for '{requested_action}' in Tab 1)."
        elif cid.startswith("max_spend = "):
            limit = float(cid.split(" = ")[1].strip())
            if float(requested_amount or 0) > limit:
                return f"Ceiling exceeded: Requested amount ${requested_amount} exceeds permitted ceiling of ${limit}."
        elif cid.startswith("disallowed_role = "):
            forbidden = cid.split(" = ")[1].strip().lower()
            if current_role == forbidden:
                return f"Protected designation: Target '{target_name}' has protected role '{forbidden}' and cannot be modified."
            if requested_role and requested_role.strip().lower() == forbidden:
                return f"Protected designation: Assigning or creating protected role '{forbidden}' is strictly forbidden."
        elif cid.startswith("disallowed_path = "):
            forbidden = cid.split(" = ")[1].strip().lower()
            if ".." in (target_path or ""):
                return "Directory traversal attack detected ('..'). Confinement boundary breached."
            if clean_path and forbidden in clean_path.lower():
                return f"Restricted vault: Target path touches protected directory '{forbidden}'."
        elif cid.startswith("allowed_path_prefix = "):
            allowed = os.path.normpath(cid.split(" = ")[1].strip())
            if not clean_path or not (clean_path.startswith(allowed) or clean_path.startswith(os.path.normpath(os.path.join(".", allowed)))):
                return f"Path boundary violation: Destination '{clean_path or target_path}' is outside authorized directory '{allowed}'."
        elif cid.startswith("disallowed_domain = "):
            forbidden = cid.split(" = ")[1].strip().lower()
            if requested_recipient and str(requested_recipient).strip().lower().endswith(forbidden):
                return f"Recipient domain blacklisted: '{requested_recipient}' belongs to forbidden domain '{forbidden}'."
        elif cid.startswith("allowed_domain = "):
            allowed = cid.split(" = ")[1].strip().lower()
            if not requested_recipient or not str(requested_recipient).strip().lower().endswith(allowed):
                return f"Recipient domain restricted: '{requested_recipient}' does not match allowed domain '{allowed}'."

    return "Cryptographic signature validation failed or caveat condition unsatisfied."

def verify_action(
    token_string, 
    requested_agent, 
    requested_action, 
    requested_amount=0, 
    requested_recipient=None, 
    target_name=None, 
    requested_role=None,
    target_path=None
):
    """
    Step 3: The Gateway checks if the action breaks any rules in the token.
    Enforces identity, action type, spend/salary limits, recipient blacklists, database protected roles, and file path sandboxes.
    """
    try:
        m = Macaroon.deserialize(token_string)
        v = Verifier()
        
        # 1. Check exact string matches
        v.satisfy_exact(f"agent_id = {requested_agent}")
        v.satisfy_exact(f"action = {requested_action}")
        
        # 2. Check dynamic spend limit or salary cap logic
        def check_spend(predicate):
            if predicate.startswith("max_spend = "):
                limit = float(predicate.split(" = ")[1])
                return float(requested_amount or 0) <= limit
            return False
            
        v.satisfy_general(check_spend)

        # 3. Check database row-level protected designations/roles (e.g. admin, executive)
        target_record = get_employee(target_name) if target_name else None
        current_role = target_record["role"].lower() if target_record else None

        def check_disallowed_role(predicate):
            if predicate.startswith("disallowed_role = "):
                forbidden = predicate.split(" = ")[1].strip().lower()
                # Target employee must not currently have a protected designation
                if current_role and current_role == forbidden:
                    return False
                # Cannot assign or create a user with a protected designation
                if requested_role and requested_role.strip().lower() == forbidden:
                    return False
                return True
            return False

        v.satisfy_general(check_disallowed_role)

        # 4. Check File Sandbox / Directory Confinement logic
        clean_path = normalize_target_path(target_path)

        def check_allowed_path(predicate):
            if predicate.startswith("allowed_path_prefix = "):
                allowed = os.path.normpath(predicate.split(" = ")[1].strip())
                if not clean_path:
                    return False
                return clean_path.startswith(allowed) or clean_path.startswith(os.path.normpath(os.path.join(".", allowed)))
            return False

        v.satisfy_general(check_allowed_path)

        def check_disallowed_path(predicate):
            if predicate.startswith("disallowed_path = "):
                forbidden = predicate.split(" = ")[1].strip().lower()
                if not clean_path:
                    return False
                # Deny directory traversal and forbidden folders
                if ".." in (target_path or ""):
                    return False
                return forbidden not in clean_path.lower()
            return False

        v.satisfy_general(check_disallowed_path)

        # 5. Check dynamic recipient domain blacklist logic (for emails)
        def check_disallowed(predicate):
            if predicate.startswith("disallowed_domain = "):
                forbidden_domain = predicate.split(" = ")[1].strip().lower()
                if not requested_recipient:
                    return False
                recipient = str(requested_recipient).strip().lower()
                return not recipient.endswith(forbidden_domain)
            return False

        v.satisfy_general(check_disallowed)

        # 6. Check dynamic recipient domain whitelist logic (if present)
        def check_domain(predicate):
            if predicate.startswith("allowed_domain = "):
                allowed_domain = predicate.split(" = ")[1].strip().lower()
                if not requested_recipient:
                    return False
                recipient = str(requested_recipient).strip().lower()
                return recipient.endswith(allowed_domain)
            return False

        v.satisfy_general(check_domain)
        
        # 7. Cryptographically verify the token hasn't been tampered with
        v.verify(m, SECRET_KEY)
        return True, "✅ Approved: Cryptographic verification passed."
        
    except Exception as e:
        diag = diagnose_rule_violation(
            token_string, 
            requested_agent, 
            requested_action, 
            requested_amount, 
            requested_recipient, 
            target_name, 
            requested_role, 
            target_path
        )
        return False, f"🛑 Blocked by Gateway: {diag}"

def send_real_email(recipient, subject, body, smtp_config=None):
    """
    Step 4: Real Implementation Execution.
    Dispatches a real RFC 5322 MIME email message.
    - If live SMTP credentials are provided, transmits it over the network.
    - Otherwise, saves it into the verified local outbox spool ('sent_emails/').
    """
    msg = EmailMessage()
    sender = (smtp_config.get("sender") or smtp_config.get("user") or "agentauth-gateway@demo.local") if smtp_config else "agentauth-gateway@demo.local"
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject or "Automated AI Agent Notification"
    msg["Date"] = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg["Message-ID"] = f"<{uuid.uuid4()}@agentauth.local>"
    msg["X-AgentAuth-Verified"] = "True"
    msg.set_content(body or "")

    # Try live SMTP network dispatch if configured
    if smtp_config and smtp_config.get("host") and smtp_config.get("user") and smtp_config.get("password"):
        host = smtp_config["host"]
        port = int(smtp_config.get("port", 587))
        user = smtp_config["user"]
        password = smtp_config["password"]
        use_ssl = smtp_config.get("ssl", False) or port == 465

        try:
            if use_ssl:
                with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                    server.login(user, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.starttls()
                    server.login(user, password)
                    server.send_message(msg)
            return True, f"Live Email Dispatched via SMTP ({host}:{port}) to {recipient}!", msg.as_string()
        except Exception as err:
            return False, f"SMTP Network Error: {str(err)}", msg.as_string()

    # Zero-config local spool fallback (guarantees real RFC MIME email creation & auditability)
    os.makedirs("sent_emails", exist_ok=True)
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"sent_emails/email_{timestamp_str}_{uuid.uuid4().hex[:6]}.eml"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(msg.as_string())

    return True, f"Real MIME Email Generated & Stored in Outbox Spool ({filepath}) to {recipient}!", msg.as_string()


# --- LOCAL TESTING ENVIRONMENT ---
# If Dev 1 runs `python token_engine.py` in the terminal, this block will execute
# and prove both spend and email restriction logic work before UI integration.
if __name__ == "__main__":
    print("--- 1. MINTING HUMAN FLIGHT TOKEN ---")
    flight_token = create_grant("TravelBot", 400.0, "book_flight")
    print(f"Token string created: {flight_token[:40]}...\n")
    
    print("--- 2. VERIFYING GOOD FLIGHT ACTION ---")
    is_valid, msg = verify_action(flight_token, "TravelBot", "book_flight", 350.0)
    print(msg) 
    
    print("\n--- 3. VERIFYING HACKER FLIGHT ACTION (SCOPE CREEP) ---")
    is_valid, msg = verify_action(flight_token, "TravelBot", "book_flight", 500.0)
    print(msg)

    print("\n--- 4. MINTING BLACKLISTED EMAIL TOKEN (FORBIDDEN RIVAL DOMAIN) ---")
    email_token = create_grant("TravelBot", 0, "send_email", blocked_domain="@rival-competitor.com, @attacker.org")
    print("Caveats inside token:", inspect_token(email_token))

    print("\n--- 5. VERIFYING LEGITIMATE CLIENT EMAIL (ALLOWED) ---")
    is_valid, msg = verify_action(email_token, "TravelBot", "send_email", 0, "partner@client-firm.com")
    print(msg)
    if is_valid:
        ok, res, _ = send_real_email("partner@client-firm.com", "Project Status Update", "Delivery is on track for next Friday.")
        print(f"Execution Result: {res}")

    print("\n--- 6. VERIFYING ROGUE EMAIL TO RIVAL COMPETITOR (BLOCKED BY GATEWAY) ---")
    is_valid, msg = verify_action(email_token, "TravelBot", "send_email", 0, "ceo@rival-competitor.com")
    print(msg)

    print("\n--- 7. MINTING DATABASE DELEGATION TOKEN (PROTECT ADMIN/EXEC, CAP $120,000) ---")
    db_token = create_grant("DBAgent", 120000.0, "update_database", blocked_roles="admin, executive")
    print("Caveats inside token:", inspect_token(db_token))

    print("\n--- 8. VERIFYING LEGITIMATE DB UPDATE (Bob Smith, Sales Rep -> $75k) ---")
    is_valid, msg = verify_action(db_token, "DBAgent", "update_database", requested_amount=75000.0, target_name="Bob Smith")
    print(msg)
    if is_valid:
        ok, res = execute_db_update("Bob Smith", "salary", 75000.0)
        print("Execution Result:", res)

    print("\n--- 9. VERIFYING ROGUE DB ATTACK ON PROTECTED ADMIN (Diana Prince -> $160k) ---")
    is_valid, msg = verify_action(db_token, "DBAgent", "update_database", requested_amount=160000.0, target_name="Diana Prince")
    print(msg)

    print("\n--- 10. MINTING DATA REDACTOR TOKEN (CONFINED TO ./workspace/public_logs/) ---")
    redactor_token = create_grant(
        "RedactorBot", 
        allowed_action="redact_data", 
        allowed_path_prefix="./workspace/public_logs/", 
        blocked_path="sys_admin_keys"
    )
    print("Caveats inside token:", inspect_token(redactor_token))

    print("\n--- 11. VERIFYING LEGITIMATE FILE REDACTION (Public Logs) ---")
    is_valid, msg = verify_action(
        redactor_token, 
        "RedactorBot", 
        "redact_data", 
        target_path="./workspace/public_logs/cleaned_support_log.txt"
    )
    print(msg)
    if is_valid:
        ok, res = execute_file_redaction("./workspace/public_logs/cleaned_support_log.txt", "Customer Phone: [REDACTED]")
        print("Execution Result:", res)

    print("\n--- 12. VERIFYING ROGUE ATTACK ON PROTECTED DIRECTORY (/sys-admin-keys/) ---")
    is_valid, msg = verify_action(
        redactor_token, 
        "RedactorBot", 
        "redact_data", 
        target_path="./workspace/sys_admin_keys/root_credentials.txt"
    )
    print(msg)

