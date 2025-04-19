"""
Authentication and user management module for the Expense Tracker application.
Handles user registration, login, session management, and access control.
"""
import streamlit as st
import json
import os
import bcrypt
import re
import time
import jsonschema
from jsonschema import validate
import hashlib
from datetime import datetime
import logging

# Try to import dotenv, but make it optional
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, provide a simple fallback
    def load_dotenv():
        pass

# Constants for file paths
USERS_FILE = "users.json"
SESSION_FILE = "session.json"

# Get default admin credentials from environment variables or use placeholders
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
DEFAULT_ADMIN_QUESTION = os.getenv("DEFAULT_ADMIN_QUESTION", "Your favorite color?")
DEFAULT_ADMIN_ANSWER = os.getenv("DEFAULT_ADMIN_ANSWER", "blue")

# Schema definition for validating the users.json file structure
USER_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[a-zA-Z0-9_]+$": {  # Username as key
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string"},
                "secret_question": {"type": "string"},
                "secret_answer": {"type": "string"},
                "role": {"type": "string", "enum": ["user", "admin"], "default": "user"},
                "last_login": {"type": ["number", "null"]},
                "last_ip": {"type": ["string", "null"]},
                "activity_log": {"type": "array", "items": {"type": "object"}},
                "login_count": {"type": "number"}
            },
            "required": ["email", "password", "secret_question", "secret_answer"]
        }
    },
    "additionalProperties": False
}

def load_users():
    """
    Load user data from users.json file. Creates the file if it doesn't exist.
    
    Returns:
        dict: Dictionary containing user data
    """
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    """
    Save user data to users.json file.
    
    Args:
        users (dict): Dictionary containing user data to save
    """
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def validate_users_file():
    """
    Validate the users.json file against the schema.
    If validation fails, reset the file to an empty state.
    """
    try:
        users = load_users()
        validate(instance=users, schema=USER_SCHEMA)
    except (jsonschema.exceptions.ValidationError, json.JSONDecodeError):
        st.error("The users.json file is corrupted or invalid. Resetting to an empty state.")
        save_users({})

def hash_password(password):
    """
    Create a secure hash of a password using bcrypt.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    """
    Verify a password against its hash.
    
    Args:
        password (str): Plain text password to verify
        hashed (str): Stored hashed password to check against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())

def authenticate(username, password):
    """
    Authenticate a user by checking username and password.
    
    Args:
        username (str): Username to authenticate
        password (str): Password to verify
        
    Returns:
        bool: True if authentication succeeds, False otherwise
    """
    users = load_users()
    user = users.get(username)
    if user and "password" in user:
        return check_password(password, user["password"])
    return False

def is_valid_email(email):
    """
    Validate email format using regex.
    
    Args:
        email (str): Email to validate
        
    Returns:
        bool: True if email format is valid, False otherwise
    """
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)

def is_strong_password(password):
    """
    Check if a password meets security requirements.
    Password must be at least 8 characters and include uppercase, 
    lowercase, digit, and special character.
    
    Args:
        password (str): Password to check
        
    Returns:
        bool: True if password is strong, False otherwise
    """
    return (
        len(password) >= 8 and
        any(c.isupper() for c in password) and
        any(c.islower() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*()_+-=" for c in password)
    )

# Whether to allow new user registration
ALLOW_SIGNUP = True

def signup():
    """
    Handle user registration with form validation.
    Creates a new user account when all validations pass.
    
    Returns:
        bool: True if registration was successful, False otherwise
    """
    if not ALLOW_SIGNUP:
        st.warning("Signups are currently disabled. Please contact the administrator.")
        return False

    with st.form("Signup Form", clear_on_submit=False):
        st.subheader("📝 Sign Up")
        account_type = st.radio("Choose Account Type", ["User", "Admin"], horizontal=True)
        username = st.text_input("Choose a Username")
        email = st.text_input("Enter Your Email")
        secret_question = st.text_input("Set a Secret Question (e.g., Your pet's name?)")
        secret_answer = st.text_input("Answer Your Secret Question")
        password = st.text_input("Choose a Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Sign Up")

        if submitted:
            # Validate email format
            EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not re.match(EMAIL_REGEX, email):
                st.error("Invalid email format.")
                return
                
            # Check if email already exists
            users = load_users()
            if any(user["email"] == email for user in users.values()):
                st.error("Email already registered.")
                return
                
            # Additional email validation
            if not is_valid_email(email):
                st.error("Invalid email format. Please enter a valid email.")
                return False
                
            # Password strength check
            if not is_strong_password(password):
                st.error("Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character.")
                return False
                
            # Check if username exists
            if username in users or any(user.get("email") == email for user in users.values()):
                st.error("Username or email already exists. Please choose a different one.")
            elif password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            else:
                # Create new user with hashed password and secret answer
                hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                users[username] = {
                    "email": email,
                    "password": hashed_password,
                    "secret_question": secret_question,
                    "secret_answer": hash_answer(secret_answer),
                    "role": account_type.lower(),
                    "last_login": None,
                    "last_ip": None,
                    "registration_date": datetime.now().isoformat()
                }
                save_users(users)
                st.success("Registration successful! You can now log in.")
                return True
    return False

def hash_answer(answer):
    """
    Hash a secret answer using SHA-256 for secure storage.
    
    Args:
        answer (str): Plain text secret answer
        
    Returns:
        str: Hashed secret answer
    """
    return hashlib.sha256(answer.encode()).hexdigest()

def reset_password():
    """
    Handle password reset flow using secret question/answer verification.
    """
    with st.form("Reset Password Form", clear_on_submit=False):
        st.subheader("🔑 Reset Password")
        username = st.text_input("Enter Your Username")
        submitted_username = st.form_submit_button("Fetch Secret Question")

        # Step 1: Fetch the secret question for the username
        if submitted_username:
            users = load_users()
            user = users.get(username)
            if not user:
                st.error("No account found with this username.")
                st.stop()
            question = user.get("secret_question", "Secret Question")
            st.session_state["secret_question"] = question

        # Display the secret question if available
        question = st.session_state.get("secret_question", "")
        if question:
            st.text(f"Your Secret Question: {question}")

        # Step 2: Verify answer and allow password reset
        secret_answer = st.text_input("Answer Your Secret Question")
        new_password = st.text_input("Enter New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password")

        if submitted:
            users = load_users()
            user = users.get(username)
            if not user:
                st.error("No account found with this username.")
            elif user.get("secret_answer") != hash_answer(secret_answer):
                st.error("Incorrect answer to the secret question.")
            elif new_password != confirm_new_password:
                st.error("Passwords do not match. Please try again.")
            else:
                # Update the password with a new hash
                hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                users[username]["password"] = hashed_password
                save_users(users)
                st.success("Password reset successful! You can now log in.")

def session_timeout():
    """
    Check if the user session has timed out due to inactivity.
    Logs out the user if timeout duration has been exceeded.
    """
    timeout_duration = 600  # 10 minutes in seconds
    last_active = st.session_state.get("last_active", time.time())
    if time.time() - last_active > timeout_duration:
        logout()
        st.error("Session timed out. Please log in again.")
        st.rerun()
    else:
        st.session_state["last_active"] = time.time()

def login_user():
    """
    Handle regular user login.
    
    Returns:
        bool: True if login was successful, False otherwise
    """
    st.subheader("🔐 User Login")
    return login(role="user")

def login_admin():
    """
    Handle admin user login.
    
    Returns:
        bool: True if login was successful, False otherwise
    """
    st.subheader("🛡️ Admin Login")
    return login(role="admin")

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "auth_status" not in st.session_state:
    st.session_state["auth_status"] = False

def save_session_state():
    """
    Save the current session state to a file for persistence.
    """
    session_data = {
        "user": st.session_state.get("user"),
        "role": st.session_state.get("role"),
        "authenticated": st.session_state.get("authenticated", False),
        "auth_status": st.session_state.get("auth_status", False)
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f)

def load_session_state():
    """
    Load the session state from a file, if available.
    """
    try:
        with open(SESSION_FILE, "r") as f:
            session_data = json.load(f)
            st.session_state["user"] = session_data.get("user")
            st.session_state["role"] = session_data.get("role")
            st.session_state["authenticated"] = session_data.get("authenticated", False)
            st.session_state["auth_status"] = session_data.get("auth_status", False)
    except FileNotFoundError:
        st.session_state["user"] = None
        st.session_state["authenticated"] = False
        st.session_state["auth_status"] = False
        st.session_state["role"] = None

def clear_session_state():
    """
    Clear the session state and remove the session file.
    Used during logout.
    """
    st.session_state.clear()
    try:
        os.remove(SESSION_FILE)
    except FileNotFoundError:
        pass

# Load session state on module import
load_session_state()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def login(role="user"):
    """
    Handle user login with email and password.
    Validates credentials and sets up session state.
    
    Args:
        role (str): Role to authenticate for ('user' or 'admin')
        
    Returns:
        bool: True if login was successful, False otherwise
    """
    users = load_users()
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        logging.debug(f"Attempting login for email: {email}")
        for user, creds in users.items():
            if creds["email"] == email:
                logging.debug(f"Email found for user: {user}")
                if check_password(password, creds["password"]):
                    # Check if user has the required role
                    if creds.get("role") == role:
                        st.success(f"Welcome, {user}!")
                        st.session_state["user"] = user
                        st.session_state["role"] = creds.get("role")
                        st.session_state["authenticated"] = True
                        st.session_state["auth_status"] = True
                        
                        # Record login activity
                        log_user_activity(user, "login")
                        
                        # Update last login timestamp
                        users[user]["last_login"] = datetime.now().isoformat()
                        save_users(users)
                        
                        save_session_state()
                        return True
                    else:
                        st.error("Invalid role for this account. Please check your login type.")
                        return False
                else:
                    logging.debug("Password mismatch.")
                    st.error("Invalid credentials. Please check your email and password.")
                    return False
        logging.debug("Email not found in users.json.")
        st.error("Invalid credentials. Please check your email and password.")
    return False

def log_user_activity(username, action_type):
    """
    Log user activity for analytics and tracking.
    
    Args:
        username (str): Username to log activity for
        action_type (str): Type of activity (login, upload, etc.)
        
    Returns:
        bool: True if activity was logged successfully, False otherwise
    """
    users = load_users()
    if username in users:
        # Initialize activity log if it doesn't exist
        if "activity_log" not in users[username]:
            users[username]["activity_log"] = []
            
        # Add new activity with timestamp
        users[username]["activity_log"].append({
            "action": action_type,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update counter for specific action type
        counter_key = f"{action_type}_count"
        if counter_key not in users[username]:
            users[username][counter_key] = 0
        users[username][counter_key] += 1
        
        save_users(users)
        return True
    return False

def logout():
    """
    Log out the current user and clear session state.
    """
    clear_session_state()
    st.success("You have been logged out.")

def is_authenticated():
    """
    Check if the user is authenticated and session is valid.
    Shows warning and stops execution if not authenticated.
    """
    if not st.session_state.get('auth_status'):
        st.warning("You must log in to access this page.")
        st.stop()
    session_timeout()

def restrict_access():
    """
    Restrict access to authenticated users only.
    Stops page execution if user is not authenticated.
    """
    if not st.session_state.get('auth_status'):
        st.warning("You must log in to access this page.")
        st.stop()

def require_admin():
    """
    Restrict access to admin users only.
    Stops page execution if user is not an admin.
    """
    if st.session_state.get("role") != "admin":
        st.warning("Admins only. You don't have access to this page.")
        st.stop()

def ensure_default_admin():
    """
    Ensure a default admin account exists.
    Creates one if no admin user is found.
    """
    users = load_users()
    if "adminuser" not in users:
        users["adminuser"] = {
            "email": DEFAULT_ADMIN_EMAIL,
            "password": hash_password(DEFAULT_ADMIN_PASSWORD),
            "secret_question": DEFAULT_ADMIN_QUESTION,
            "secret_answer": hash_answer(DEFAULT_ADMIN_ANSWER),
            "role": "admin",
            "last_login": None,
            "last_ip": None,
            "activity_log": [],
            "login_count": 0,
            "upload_count": 0,
            "registration_date": datetime.now().isoformat()
        }
        save_users(users)

def validate_user_hashes():
    """
    Validate the password hashes in the users database.
    For debugging purposes.
    """
    users = load_users()
    for username, user_data in users.items():
        logging.debug(f"Validating user: {username}")
        # Don't validate with hardcoded passwords
        pass

# Initialize admin account and validate users file
ensure_default_admin()
validate_users_file()