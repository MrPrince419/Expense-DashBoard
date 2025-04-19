"""
Main entry point for the Expense Tracker application.
Handles login, signup, and main navigation for the application.
This file serves as the landing page and manages user authentication state.
"""
import streamlit as st
from auth import login_user, login_admin, signup, logout, load_users
from utils import load_user_data, save_user_data

# Configure the Streamlit page with title, icon and layout
st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

st.title("💼 Welcome to Expense Tracker")
st.markdown("Easily track your income, expenses, and more.")

# Initialize session state variables if they don't exist
if "user" not in st.session_state:
    st.session_state["user"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "auth_status" not in st.session_state:
    st.session_state["auth_status"] = False

# Authentication flow: Show login/signup if not authenticated
if not st.session_state.get("authenticated"):
    # Create tabs for login and signup
    tabs = st.tabs(["Login", "Sign Up"])

    # Login tab functionality
    with tabs[0]:
        # Radio button to choose login type (user or admin)
        login_choice = st.radio("Choose Login Type", ["User", "Admin"], horizontal=True)

        # User login form and handler
        if login_choice == "User":
            if login_user():
                # Set session state after successful login
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "user"
                # Redirect to the upload page
                st.switch_page("pages/1_Upload.py")
        # Admin login form and handler
        elif login_choice == "Admin":
            if login_admin():
                # Set session state after successful admin login
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "admin"
                # Redirect to the admin panel
                st.switch_page("pages/admin_panel.py")

    # Signup tab functionality
    with tabs[1]:
        signup()
# If already authenticated, show welcome message and navigation options
else:
    # Welcome message with username
    st.success(f"Welcome back, {st.session_state.get('user', 'User')}!")
    
    # Navigation buttons to main pages
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Upload Page"):
            st.switch_page("pages/1_Upload.py")
    with col2:
        if st.button("Go to Dashboard"):
            st.switch_page("pages/2_Dashboard.py")
    
    # Sign out button
    if st.button("Sign Out", type="primary"):
        logout()
        st.rerun()