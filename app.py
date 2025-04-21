"""
Main entry point for the Expense Tracker application.
Handles login, signup, forgot password, and main navigation for the application.
This file serves as the landing page and manages user authentication state.
"""
import streamlit as st
import json
from auth import signup, logout, initialize_session_state, login, reset_password, hash_password, load_users, save_users, hash_answer, check_password
from utils import load_user_data, save_user_data, get_transactions

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
        email = st.text_input("Enter your email", key="forgot_email").strip()
        if st.button("Verify Email", key="verify_email_button"):
            users = load_users()
            
            # Check both as direct key and in email field
            user_email = None
            if email in users:
                user_email = email
            else:
                for username, user in users.items():
                    if user.get("email") == email:
                        user_email = username
                        break
            
            if not user_email:
                st.error("Email does not exist.")
                return
                
            st.session_state.fp_verified_user = user_email
            st.session_state.fp_email_verified = True
            st.success("Email verified. Please answer your secret question.")
    
    # Secret question and password reset step
    if st.session_state.fp_email_verified and st.session_state.fp_verified_user:
        user_email = st.session_state.fp_verified_user
        users = load_users()
        
        # Get user data
        user_data = users.get(user_email, {})
        
        secret_question = user_data.get("secret_question", "Secret Question")
        st.text(f"Your Secret Question: {secret_question}")
        secret_answer = st.text_input("Answer Your Secret Question", key="forgot_answer").strip()

        # Add warning for capitalization
        if secret_answer and not secret_answer.islower():
            st.warning("Warning: Your answer contains capital letters. Ensure it matches exactly.")

        new_password = st.text_input("Enter New Password", type="password", key="forgot_new_password").strip()
        confirm_new_password = st.text_input("Confirm New Password", type="password", key="forgot_confirm_password").strip()

        if st.button("Reset Password", key="reset_password_button"):
            if hash_answer(secret_answer) != user_data.get("secret_answer"):
                st.error("Incorrect answer to the secret question.")
                return
            
            if new_password != confirm_new_password:
                st.error("Passwords do not match. Please try again.")
                return
                
            # Update password in user data
            if user_email in users:
                users[user_email]["password"] = hash_password(new_password)
                save_users(users)
                
                st.success("Password reset successful! You can now log in.")
                st.session_state.fp_email_verified = False
                st.session_state.fp_verified_user = None
            else:
                st.error("User not found.")

if not st.session_state.get("authenticated"):
    tabs = st.tabs(["Login", "Sign Up", "Forgot Password"])

    # Login Tab
    with tabs[0]:
        login_choice = st.selectbox("Choose Login Type", ["User", "Admin"], key="login_type")

        # Add admin credentials info when Admin is selected
        if login_choice == "Admin":
            st.info("For admin access, use these credentials:\n- Email: admin@example.com\n- Password: Admin@123456\n\nNote: Admin accounts can only log in via Admin login.")
            if login(role="admin"):
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "admin"
                
                try:
                    st.switch_page("pages/admin_panel.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit. Please update Streamlit.")
        else:
            st.info("Regular user login. Note: Admin accounts must use the Admin login option.")
            if login(role="user"):
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                
                # Load user's transaction data immediately after login
                if "user" in st.session_state:
                    try:
                        get_transactions()  # This will load data into session state
                    except Exception as e:
                        st.warning(f"Could not load your saved data: {e}")
                
                try:
                    st.switch_page("pages/1_Upload.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit. Please update Streamlit.")

    # Signup Tab
    with tabs[1]:
        signup()

    # Forgot Password Tab
    with tabs[2]:
        forgot_password()

else:
    st.success(f"Welcome back, {st.session_state.get('user', 'User')}!")
    
    # Show data persistence status if available
    if "transactions" in st.session_state and not st.session_state["transactions"].empty:
        st.info(f"🔄 Your data is ready: {len(st.session_state['transactions'])} transactions loaded.")
    
    # Show admin options if user is an admin
    if st.session_state.get("role") == "admin":
        st.info("🔑 You have administrator privileges.")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Go to Upload Page", key="go_to_upload"):
                try:
                    st.switch_page("pages/1_Upload.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit.")
        
        with col2:
            if st.button("Go to Dashboard", key="go_to_dashboard"):
                try:
                    st.switch_page("pages/2_Dashboard.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit.")
        
        with col3:
            if st.button("Go to Admin Panel", key="go_to_admin"):
                try:
                    st.switch_page("pages/admin_panel.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit.")
    else:
        # Regular user navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go to Upload Page", key="go_to_upload"):
                try:
                    st.switch_page("pages/1_Upload.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit.")
        with col2:
            if st.button("Go to Dashboard", key="go_to_dashboard"):
                try:
                    st.switch_page("pages/2_Dashboard.py")
                except AttributeError:
                    st.warning("Navigation is not supported in this version of Streamlit.")
    
    if st.button("Sign Out", type="primary", key="sign_out"):
        # Save any data before logging out
        if "transactions" in st.session_state and "user" in st.session_state:
            try:
                email = st.session_state["user"]
                metadata = {
                    "last_upload_filename": st.session_state.get("uploaded_file_name", "Unknown"),
                    "last_upload_timestamp": st.session_state.get("upload_timestamp", "Unknown"),
                    "upload_history": st.session_state.get("upload_history", [])
                }
                save_user_data(email, st.session_state["transactions"], metadata)
                st.success("Your data has been saved.")
            except Exception as e:
                st.error(f"Could not save your data: {e}")
        
        logout()  # Immediately sign out the user/admin
        st.rerun()  # Use st.rerun() instead of st.stop() for cleaner page refresh