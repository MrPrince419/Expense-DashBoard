"""
Authentication module for the Expense Tracker application.
Handles user login, registration, password management, and access control.
"""
import streamlit as st
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
import re
import logging
from passlib.hash import pbkdf2_sha256  # For compatibility with existing hashes

# Set up logging for authentication issues
logging.basicConfig(
    filename="auth_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration
USER_DATA_DIR = Path("user_data")
USER_DB_FILE = Path("users.json")  # Path directly to the existing users.json

def initialize_session_state():
    """Initialize session state variables for authentication."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "auth_status" not in st.session_state:
        st.session_state["auth_status"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "role" not in st.session_state:
        st.session_state["role"] = None
    if "active_sessions" not in st.session_state:
        st.session_state["active_sessions"] = []

def load_users():
    """Load user data from the JSON file."""
    # Create file if it doesn't exist
    if not USER_DB_FILE.exists():
        with open(USER_DB_FILE, "w") as f:
            json.dump({}, f)
    
    try:
        with open(USER_DB_FILE, "r") as f:
            users = json.load(f)
            
            # Debug output for admin credentials
            if "admin@example.com" in users:
                admin = users["admin@example.com"]
                logging.debug(f"Admin user found: {admin.get('email')}, role: {admin.get('role')}")
            else:
                logging.debug("Admin user not found in users.json")
            
            return users
    except json.JSONDecodeError as e:
        logging.error(f"Error loading users.json: {e}")
        # If the file is corrupted, return an empty dict
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading users: {e}")
        return {}

def save_users(users):
    """Save user data to the JSON file."""
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=4)

def ensure_admin_exists():
    """
    Ensure admin account exists with correct credentials, without reset functionality.
    """
    users = load_users()
    admin_email = "admin@example.com"
    admin_password = "Admin@123456"
    
    # Check if admin account exists, create if not
    if admin_email not in users:
        # Create admin account if it doesn't exist
        users[admin_email] = {
            "email": admin_email,
            "password": pbkdf2_sha256.hash(admin_password),
            "role": "admin",
            "secret_question": "Your favorite color?",
            "secret_answer": hash_answer("blue"),
            "registration_date": datetime.now().isoformat(),
            "last_login": None,
            "activity_log": []
        }
        save_users(users)
        logging.info("Created default admin account")

def hash_password(password):
    """
    Create password hash using either passlib (for compatibility) or SHA-256.
    This allows working with existing hashed passwords in the database.
    """
    # Always use passlib for new passwords
    return pbkdf2_sha256.hash(password)

def hash_answer(answer):
    """Create a hash of the secret answer (case-insensitive)."""
    return hashlib.sha256(answer.lower().encode()).hexdigest()

def check_password(password, hashed_password):
    """
    Check if the password matches the hashed password.
    Supports both passlib format and simple SHA-256.
    """
    try:
        if hashed_password.startswith('$pbkdf2'):
            # Use passlib for verification
            match = pbkdf2_sha256.verify(password, hashed_password)
            logging.debug(f"Password check using pbkdf2: {'match' if match else 'no match'}")
            return match
        else:
            # Fallback to simple SHA-256
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            match = (password_hash == hashed_password)
            logging.debug(f"Password check using SHA-256: {'match' if match else 'no match'}")
            return match
    except Exception as e:
        logging.error(f"Password verification error: {e}")
        return False

def login(role="user"):
    """Handle user login with email as identifier."""
    st.subheader("Login")
    
    email = st.text_input("Email Address", key="login_email").strip()
    password = st.text_input("Password", type="password", key="login_password").strip()
    
    if st.button("Login", key="login_button"):
        if not email or not password:
            st.error("Email and password cannot be empty.")
            return False
        
        users = load_users()
        
        # Check if email exists as a key
        if email in users:
            user_data = users[email]
        else:
            # Try to find by the email field inside each user
            email_match = None
            for username, user in users.items():
                if user.get("email") == email:
                    email_match = username
                    break
            
            if email_match:
                user_data = users[email_match]
                # Update the user's entry to use email as key for future logins
                users[email] = users[email_match]
                del users[email_match]
                save_users(users)
            else:
                st.error("Email not found. Please sign up first.")
                return False
        
        # Check password
        if not check_password(password, user_data["password"]):
            st.error("Incorrect password. Please try again.")
            return False
            
        # Strict role enforcement: Ensure admin can only log in to admin interface and users to user interface
        user_role = user_data.get("role", "user")
        if (role == "admin" and user_role != "admin") or (role == "user" and user_role == "admin"):
            if role == "admin":
                st.error("This account doesn't have admin privileges.")
            else:
                st.error("Admin accounts must use the Admin login option.")
            return False
        
        # Login successful
        st.session_state["user"] = email
        st.session_state["authenticated"] = True
        st.session_state["role"] = user_role
        
        # Add to active sessions
        if email not in st.session_state.get("active_sessions", []):
            active_sessions = st.session_state.get("active_sessions", [])
            active_sessions.append(email)
            st.session_state["active_sessions"] = active_sessions
        
        # Log this login
        now = datetime.now().isoformat()
        users[email]["last_login"] = now
        users[email]["login_count"] = users[email].get("login_count", 0) + 1
        
        # Add login to activity log
        if "activity_log" not in users[email]:
            users[email]["activity_log"] = []
        
        users[email]["activity_log"].append({
            "action": "login",
            "timestamp": now,
            "ip": os.environ.get("REMOTE_ADDR", "unknown")
        })
        
        save_users(users)
        log_user_activity(email, "login")
        
        # Load user data on successful login
        try:
            from utils import get_transactions
            get_transactions()
        except Exception as e:
            logging.warning(f"Could not load transaction data: {e}")
            
        return True
    
    return False

def signup():
    """Handle user registration with email as identifier."""
    st.subheader("Create an Account")
    
    # Input fields
    email = st.text_input("Email Address", key="signup_email").strip()
    password = st.text_input("Password", type="password", key="signup_password").strip()
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password").strip()
    
    # Security question for password recovery
    secret_question = st.text_input("Set a Secret Question for Password Recovery", key="signup_question").strip()
    secret_answer = st.text_input("Answer to Your Secret Question", key="signup_answer").strip()
    
    if secret_answer and not secret_answer.islower():
        st.warning("Your answer will be stored in lowercase for easier recovery.")
    
    if st.button("Sign Up", key="signup_button"):
        # Validate inputs
        if not email or not password:
            st.error("All fields are required.")
            return
            
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
            
        if not secret_question or not secret_answer:
            st.error("Security question and answer are required for account recovery.")
            return
        
        # Email validation (basic check)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            st.error("Please enter a valid email address.")
            return
            
        # Check if email already exists
        users = load_users()
        
        # Check direct email key and email field in all users
        email_exists = False
        if email in users:
            email_exists = True
        else:
            for user in users.values():
                if user.get("email") == email:
                    email_exists = True
                    break
        
        if email_exists:
            st.error("Email already registered. Please login or use a different email.")
            return
        
        # Create new user
        users[email] = {
            "email": email,
            "password": hash_password(password),
            "secret_question": secret_question,
            "secret_answer": hash_answer(secret_answer),
            "role": "user",  # Default role
            "registration_date": datetime.now().isoformat(),
            "last_login": None,
            "login_count": 0,
            "upload_count": 0,
            "activity_log": []
        }
        
        save_users(users)
        st.success("Account created successfully! You can now log in.")

def reset_password(email, new_password):
    """Reset a user's password."""
    users = load_users()
    if email not in users:
        # Try to find by email field
        for username, user in users.items():
            if user.get("email") == email:
                users[username]["password"] = hash_password(new_password)
                save_users(users)
                return True
        return False
    
    users[email]["password"] = hash_password(new_password)
    save_users(users)
    return True

def logout():
    """Log out the current user and clear session state."""
    # Save transaction data before logout if available
    if "user" in st.session_state and "transactions" in st.session_state:
        from utils import save_user_data
        try:
            email = st.session_state["user"]
            metadata = {
                "last_upload_filename": st.session_state.get("uploaded_file_name", "Unknown"),
                "last_upload_timestamp": st.session_state.get("upload_timestamp", "Unknown"),
                "upload_history": st.session_state.get("upload_history", [])
            }
            save_user_data(email, st.session_state["transactions"], metadata)
            
            # Log logout activity
            log_user_activity(email, "logout")
            
            # Remove from active sessions
            if email in st.session_state.get("active_sessions", []):
                active_sessions = st.session_state.get("active_sessions", [])
                active_sessions.remove(email)
                st.session_state["active_sessions"] = active_sessions
                
        except Exception:
            pass  # Silently fail if saving doesn't work
    
    # Clear authentication status
    st.session_state["authenticated"] = False
    st.session_state["auth_status"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None
    
    # We intentionally don't clear transactions to support future logins

def restrict_access():
    """Ensure only authenticated users can access the page."""
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.error("Please login to access this page.")
        st.stop()

def require_admin():
    """Ensure only admin users can access the page."""
    # Make sure admin account exists
    ensure_admin_exists()
    
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.error("Please login to access this page.")
        st.stop()
        
    if "role" not in st.session_state or st.session_state["role"] != "admin":
        st.error("You need admin privileges to access this page.")
        st.info("To access the admin panel, you must use the Admin login with admin credentials.")
        st.stop()
    
    # Log successful admin access
    if "user" in st.session_state:
        log_user_activity(st.session_state["user"], "admin_access")

def log_user_activity(user_email, action, details=None):
    """
    Log user activity in the user's activity log.
    
    Args:
        user_email (str): The email of the user
        action (str): The action being performed (e.g. login, upload, etc.)
        details (dict, optional): Additional details about the action
    """
    if not user_email:
        return
        
    users = load_users()
    if user_email not in users:
        # Try to find by email field
        user_key = None
        for username, user in users.items():
            if user.get("email") == user_email:
                user_key = username
                break
                
        if not user_key:
            return
    else:
        user_key = user_email
    
    # Make sure activity log exists
    if "activity_log" not in users[user_key]:
        users[user_key]["activity_log"] = []
    
    # Create activity entry
    activity = {
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "ip": os.environ.get("REMOTE_ADDR", "unknown")
    }
    
    if details:
        activity.update(details)
    
    # Update counters based on action
    if action == "upload":
        users[user_key]["upload_count"] = users[user_key].get("upload_count", 0) + 1
    
    # Add to activity log
    users[user_key]["activity_log"].append(activity)
    save_users(users)