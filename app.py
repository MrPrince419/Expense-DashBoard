"""
Main entry point for the Expense Tracker application.
Handles login, signup, forgot password, and main navigation for the application.
This file serves as the landing page and manages user authentication state.
"""
import streamlit as st
import json
from auth import signup, logout, initialize_session_state, login, reset_password, hash_password, load_users, save_users, hash_answer, check_password
from utils import load_user_data, save_user_data

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

st.title("💼 Welcome to Expense Tracker")
st.markdown("Easily track your income, expenses, and more.")

# Initialize session state
initialize_session_state()

def forgot_password():
    st.subheader("Forgot Password")

    # Initialize session state variables
    if "fp_email_verified" not in st.session_state:
        st.session_state.fp_email_verified = False
    if "fp_verified_user" not in st.session_state:
        st.session_state.fp_verified_user = None

    # Email entry step
    if not st.session_state.fp_email_verified:
        email = st.text_input("Enter your email").strip()
        if st.button("Verify Email"):
            users = load_users()
            user = next((u for u in users.values() if u["email"] == email), None)
            if not user:
                st.error("Email does not exist.")
                return
            st.session_state.fp_verified_user = user
            st.session_state.fp_email_verified = True
            st.success("Email verified. Please answer your secret question.")
    
    # Secret question and password reset step
    if st.session_state.fp_email_verified and st.session_state.fp_verified_user:
        user = st.session_state.fp_verified_user
        secret_question = user.get("secret_question", "Secret Question")
        st.text(f"Your Secret Question: {secret_question}")
        secret_answer = st.text_input("Answer Your Secret Question").strip()

        # Add warning for capitalization
        if secret_answer and not secret_answer.islower():
            st.warning("Warning: Your answer contains capital letters. Ensure it matches exactly.")

        new_password = st.text_input("Enter New Password", type="password").strip()
        confirm_new_password = st.text_input("Confirm New Password", type="password").strip()

        if st.button("Reset Password"):
            if hash_answer(secret_answer) != user.get("secret_answer"):
                st.error("Incorrect answer to the secret question.")
                return
            if check_password(new_password, user["password"]):  # Compare hashed passwords
                st.error("New password cannot be the same as the old password. Please choose a different password.")
                return
            if new_password != confirm_new_password:
                st.error("Passwords do not match. Please try again.")
                return
            user["password"] = hash_password(new_password)
            users = load_users()
            for k, v in users.items():
                if v["email"] == user["email"]:
                    users[k] = user
                    break
            save_users(users)
            st.success("Password reset successful! You can now log in.")
            st.session_state.fp_email_verified = False
            st.session_state.fp_verified_user = None

if not st.session_state.get("authenticated"):
    tabs = st.tabs(["Login", "Sign Up", "Forgot Password"])

    # Login Tab
    with tabs[0]:
        login_choice = st.selectbox("Choose Login Type", ["User", "Admin"])

        if login_choice == "User":
            if login(role="user"):
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "user"
                try:
                    st.switch_page("pages/1_Upload.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit. Please update Streamlit.")
        elif login_choice == "Admin":
            if login(role="admin"):
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "admin"
                try:
                    st.switch_page("pages/admin_panel.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit. Please update Streamlit.")

        st.markdown("**Tip:** If you've forgotten your password, head over to the [Forgot Password](#) section.")

    # Signup Tab
    with tabs[1]:
        signup()

    # Forgot Password Tab
    with tabs[2]:
        forgot_password()

else:
    st.success(f"Welcome back, {st.session_state.get('user', 'User')}!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Upload Page"):
            try:
                st.switch_page("pages/1_Upload.py")
            except AttributeError:
                st.warning("Navigation is not supported in this version of Streamlit. Please update Streamlit.")
    with col2:
        if st.button("Go to Dashboard"):
            try:
                st.switch_page("pages/2_Dashboard.py")
            except AttributeError:
                st.warning("Navigation is not supported in this version of Streamlit. Please update Streamlit.")
    
    if st.button("Sign Out", type="primary"):
        logout()  # Immediately sign out the user/admin
        st.stop()  # Halt the script and force a rerun