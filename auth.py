"""
Authentication and user management module for the Expense Tracker application.
Handles user registration, login, session management, and access control.
"""
import streamlit as st
import json
import os
from passlib.hash import pbkdf2_sha256
import re
from datetime import datetime
from pathlib import Path
import logging
import hashlib  # Add this import to resolve the NameError
from jsonschema import validate  # Add this import to resolve the NameError
import time  # Add this import for session_timeout

# Configure logging
logging.basicConfig(
    filename="auth.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants for file paths
USERS_FILE = Path("users.json")
SESSION_FILE = Path("session.json")

# Get default admin credentials from environment variables or use placeholders
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
DEFAULT_ADMIN_QUESTION = os.getenv("DEFAULT_ADMIN_QUESTION", "Your favorite color?")
DEFAULT_ADMIN_ANSWER = os.getenv("DEFAULT_ADMIN_ANSWER", "blue")

# Schema definition for validating the users.json file structure
USER_SCHEMA = {
    "type": "object",
    "patternProperties": {
        # Allow email addresses as keys
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string"},
                "secret_question": {"type": "string"},
                "secret_answer": {"type": "string"},
                "role": {"type": "string", "enum": ["user", "admin"], "default": "user"},
                "last_login": {"type": ["string", "number", "null"], "format": "date-time"},
                "last_ip": {"type": ["string", "null"]},
                "activity_log": {"type": "array", "items": {"type": "object"}},
                "login_count": {"type": "number"},
            },
            "required": ["email", "password", "secret_question", "secret_answer"],
        }
    },
    # Allow specific non-email keys like "adminuser"
    "properties": {
        "adminuser": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string"},
                "secret_question": {"type": "string"},
                "secret_answer": {"type": "string"},
                "role": {"type": "string", "enum": ["admin"], "default": "admin"},
                "last_login": {"type": ["string", "number", "null"], "format": "date-time"},
                "last_ip": {"type": ["string", "null"]},
                "activity_log": {"type": "array", "items": {"type": "object"}},
                "login_count": {"type": "number"},
                "upload_count": {"type": "number"},
                "registration_date": {"type": "string", "format": "date-time"},
            },
            "required": ["email", "password", "secret_question", "secret_answer"],
        }
    },
    "additionalProperties": False,
}

def load_users():
    """
    Load users from the users.json file.
    Creates an empty file if it doesn't exist or resets it if corrupted.
    """
    try:
        if not USERS_FILE.exists():
            with USERS_FILE.open("w") as f:
                json.dump({}, f)
        with USERS_FILE.open("r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        # Handle corrupted file
        with USERS_FILE.open("w") as f:
            json.dump({}, f)
        logging.error("The users.json file was corrupted and has been reset.")
        return {}
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {USERS_FILE}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while loading users: {e}")

def save_users(users):
    """
    Save users to the users.json file.
    """
    try:
        with USERS_FILE.open("w") as f:
            json.dump(users, f, indent=4)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {USERS_FILE}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while saving users: {e}")

def validate_users_file():
    """
    Validate the structure of the users.json file.
    Resets the file if it is corrupted or invalid.
    """
    try:
        with USERS_FILE.open("r") as f:
            users = json.load(f)
            validate(instance=users, schema=USER_SCHEMA)
    except (json.JSONDecodeError, FileNotFoundError):
        with USERS_FILE.open("w") as f:
            json.dump({}, f)
        st.error("The users.json file is corrupted or invalid. Resetting to an empty state.")

def hash_password(password):
    return pbkdf2_sha256.hash(password)

def check_password(password, hashed):
    return pbkdf2_sha256.verify(password, hashed)

def authenticate(username, password):
    users = load_users()
    user = users.get(username)
    if user and "password" in user:
        return check_password(password, user["password"])
    return False

def validate_email(email):
    """
    Validates the format of an email address.
    """
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def is_strong_password(password):
    return (
        len(password) >= 8 and
        any(c.isupper() for c in password) and
        any(c.islower() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*()_+-=" for c in password)
    )

ALLOW_SIGNUP = True

def signup():
    st.subheader("Sign Up")
    if "signup_email" not in st.session_state:
        st.session_state.signup_email = ""
    if "signup_password" not in st.session_state:
        st.session_state.signup_password = ""
    if "signup_confirm_password" not in st.session_state:
        st.session_state.signup_confirm_password = ""
    if "signup_secret_answer" not in st.session_state:
        st.session_state.signup_secret_answer = ""

    email = st.text_input("Enter Your Email", value=st.session_state.signup_email, key="signup_email").strip()
    password = st.text_input("Choose a Password", type="password", value=st.session_state.signup_password, key="signup_password").strip()
    confirm_password = st.text_input("Confirm Password", type="password", value=st.session_state.signup_confirm_password, key="signup_confirm_password").strip()
    
    common_questions = [
        "What is your mother's maiden name?",
        "What was the name of your first pet?",
        "What was the make of your first car?",
        "What is your favorite book?",
        "What is your favorite movie?",
        "What is your favorite food?",
        "What city were you born in?",
        "What is your favorite color?",
        "What is your father's middle name?",
        "What was the name of your elementary school?",
        "What is your favorite sports team?",
        "What is your childhood nickname?"
    ]
    secret_question = st.selectbox("Choose a Secret Question", common_questions)
    secret_answer = st.text_input("Answer Your Secret Question", value=st.session_state.signup_secret_answer, key="signup_secret_answer").strip()
    
    all_fields_filled = all([email, password, confirm_password, secret_question, secret_answer])
    signup_button = st.button("Sign Up", disabled=not all_fields_filled)

    if signup_button:
        if not email or not password or not confirm_password or not secret_question or not secret_answer:
            st.error("All fields are required. Please fill in all fields.")
            return
        if password != confirm_password:
            st.error("Passwords do not match. Please try again.")
            return
        if not validate_email(email):
            st.error("Invalid email format. Please enter a valid email.")
            return
        if not is_strong_password(password):
            st.error("Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character.")
            return

        users = load_users()
        if any(user.get("email") == email for user in users.values()):
            st.error("Email already exists. Please choose a different one.")
            return

        hashed_password = hash_password(password)
        new_user = {
            "email": email,
            "password": hashed_password,
            "secret_question": secret_question,
            "secret_answer": hash_answer(secret_answer)
        }
        users[email] = new_user
        save_users(users)
        st.success("Signup successful! You can now log in.")
        # Clear all session state variables
        st.session_state.clear()

def hash_answer(answer):
    return hashlib.sha256(answer.encode()).hexdigest()

def reset_password():
    with st.form("Reset Password Form", clear_on_submit=False):
        st.subheader("🔑 Reset Password")
        username = st.text_input("Enter Your Username")
        submitted_username = st.form_submit_button("Fetch Secret Question")

        if submitted_username:
            users = load_users()
            user = users.get(username)
            if not user:
                st.error("No account found with this username.")
                return  # Avoid `st.stop()`
            question = user.get("secret_question", "Secret Question")
            st.session_state["secret_question"] = question

        question = st.session_state.get("secret_question", "")
        if question:
            st.text(f"Your Secret Question: {question}")
    with st.form("Reset Password Form", clear_on_submit=False):
        secret_answer = st.text_input("Answer Your Secret Question")
        new_password = st.text_input("Enter New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password")
        if submitted:
            users = load_users()
            user = users.get(username)
            if not user:
                st.error("No account found with this username.")
                return  # Avoid `st.stop()`
            elif user.get("secret_answer") != hash_answer(secret_answer):
                st.error("Incorrect answer to the secret question.")
            elif new_password != confirm_new_password:
                st.error("Passwords do not match. Please try again.")
            else:
                hashed_password = hash_password(new_password)
                users[username]["password"] = hashed_password
                save_users(users)
                st.success("Password reset successful! You can now log in.")

def session_timeout():
    timeout_duration = 600
    last_active = st.session_state.get("last_active", time.time())
    if time.time() - last_active > timeout_duration:
        logout()
        st.error("Session timed out. Please log in again.")
        st.rerun()
    else:
        st.session_state["last_active"] = time.time()

def login(role="user"):
    """
    Generalized login function for both users and admins.
    """
    st.subheader(f"🔐 {role.capitalize()} Login")
    users = load_users()
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")
    last_active = st.session_state.get("last_active", time.time())
    if "failed_attempts" not in st.session_state:
        st.session_state["failed_attempts"] = 0
    if st.session_state["failed_attempts"] >= 5:
        st.error("Too many failed login attempts. Try again later.")
        return False
    if login_btn:
        user = next((u for u, creds in users.items() if creds["email"] == email), None)
        if user:
            creds = users[user]
            if check_password(password, creds["password"]):
                if creds.get("role") == role or role == "user":  # Allow user role to log in without strict matching
                    st.success(f"Welcome, {user}!")
                    st.session_state["user"] = user
                    st.session_state["role"] = creds["role"]
                    st.session_state["authenticated"] = True
                    st.session_state["auth_status"] = True
                    st.session_state["failed_attempts"] = 0  # Reset on success
                    log_user_activity(user, "login")
                    users[user]["last_login"] = datetime.now().isoformat()
                    users[user]["last_ip"] = "127.0.0.1"  # Replace with actual IP retrieval logic
                    save_users(users)
                    save_session_state()
                    return True
                else:
                    st.error("Wrong role for this account.")
                    return False
            else:
                st.session_state["failed_attempts"] += 1
                st.error("Incorrect password.")
                return False
        st.error("Email not found.")
        st.session_state["failed_attempts"] += 1
    return False

def initialize_session_state():
    """
    Initialize session state variables if they don't exist.
    """
    default_values = {
        "authenticated": False,
        "user": None,
        "role": None,
        "auth_status": False,
        "last_active": None,
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

def save_session_state():
    session_data = {
        "user": st.session_state.get("user"),
        "role": st.session_state.get("role"),
        "authenticated": st.session_state.get("authenticated", False),
        "auth_status": st.session_state.get("auth_status", False)
    }
    with SESSION_FILE.open("w") as f:
        json.dump(session_data, f)

def load_session_state():
    try:
        with SESSION_FILE.open("r") as f:
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
    st.session_state.clear()
    try:
        SESSION_FILE.unlink()
    except FileNotFoundError:
        pass

load_session_state()

def log_user_activity(username, action):
    """
    Logs user activity with a timestamp and writes to a log file.
    """
    users = load_users()
    if username in users:
        if "activity_log" not in users[username]:
            users[username]["activity_log"] = []
        users[username]["activity_log"].append({
            "action": action,
            "timestamp": datetime.now().isoformat()
        })
        counter_key = f"{action}_count"
        if counter_key not in users[username]:
            users[username][counter_key] = 0
        users[username][counter_key] += 1
        save_users(users)
        logging.info(f"User '{username}' performed action: {action}")
        return True
    logging.warning(f"Attempted to log activity for non-existent user: {username}")
    return False

def logout():
    """
    Logs out the current user by clearing the session state and halting the script.
    """
    clear_session_state()
    st.success("You have been logged out.")
    st.stop()  # Halt the script to force a rerun

def is_authenticated():
    if not st.session_state.get('auth_status'):
        st.warning("You must log in to access this page.")
        st.stop()
    session_timeout()

def restrict_access():
    if not st.session_state.get('auth_status'):
        st.warning("You must log in to access this page.")
        st.stop()

def require_admin():
    if st.session_state.get("role") != "admin":
        st.warning("Admins only. You don't have access to this page.")
        st.stop()

def ensure_default_admin():
    """
    Ensure the default admin user exists in the users.json file with the specified credentials.
    """
    users = load_users()
    admin_email = "admin@example.com"
    admin_password = "Admin@123456"
    admin_hashed_password = hash_password(admin_password)
    admin_hashed_answer = hash_answer("blue")  # Default secret answer

    if "adminuser" not in users or users["adminuser"]["email"] != admin_email:
        users["adminuser"] = {
            "email": admin_email,
            "password": admin_hashed_password,
            "secret_question": "Your favorite color?",
            "secret_answer": admin_hashed_answer,
            "role": "admin",
            "last_login": None,
            "last_ip": None,
            "activity_log": [],
            "login_count": 0,
            "upload_count": 0,
            "registration_date": datetime.now().isoformat()
        }
    else:
        # Ensure the admin credentials are always updated
        users["adminuser"]["password"] = admin_hashed_password
        users["adminuser"]["secret_question"] = "Your favorite color?"
        users["adminuser"]["secret_answer"] = admin_hashed_answer
    save_users(users)

def validate_users():
    """
    Validate all user entries in the users.json file and ensure required keys are present.
    """
    users = load_users()
    updated = False

    for username, user_data in users.items():
        # Ensure the "role" key is present
        if "role" not in user_data:
            user_data["role"] = "user"  # Default role
            updated = True

    if updated:
        save_users(users)
        logging.info("The users.json file was updated to include missing keys.")

def validate_user_hashes():
    """
    Validates the integrity of user password and secret answer hashes.
    Logs any inconsistencies.
    """
    users = load_users()
    for username, user_data in users.items():
        if username == "adminuser":
            if not pbkdf2_sha256.verify(DEFAULT_ADMIN_PASSWORD, user_data["password"]):
                logging.warning(f"Password hash mismatch for default admin")
            if hash_answer(DEFAULT_ADMIN_ANSWER) != user_data["secret_answer"]:
                logging.warning(f"Secret answer hash mismatch for default admin")

ensure_default_admin()
validate_users_file()
validate_users()  # Ensure all user entries are valid