import streamlit as st
from auth import login_user, login_admin, signup, logout, load_users
from utils import load_user_data, save_user_data

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

st.title("💼 Welcome to Expense Tracker")
st.markdown("Easily track your income, expenses, and more.")

if "user" not in st.session_state:
    st.session_state["user"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "auth_status" not in st.session_state:
    st.session_state["auth_status"] = False

if not st.session_state.get("authenticated"):
    tabs = st.tabs(["Login", "Sign Up"])

    with tabs[0]:
        login_choice = st.radio("Choose Login Type", ["User", "Admin"], horizontal=True)

        if login_choice == "User":
            if login_user():
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "user"
                st.switch_page("pages/1_Upload.py")
        elif login_choice == "Admin":
            if login_admin():
                st.session_state["authenticated"] = True
                st.session_state["auth_status"] = True
                st.session_state["role"] = "admin"
                st.switch_page("pages/admin_panel.py")

    with tabs[1]:
        signup()
else:
    st.success(f"Welcome back, {st.session_state.get('user', 'User')}!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Upload Page"):
            st.switch_page("pages/1_Upload.py")
    with col2:
        if st.button("Go to Dashboard"):
            st.switch_page("pages/2_Dashboard.py")
    
    if st.button("Sign Out", type="primary"):
        logout()
        st.rerun()