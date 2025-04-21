"""
Admin Panel for the Expense Tracker application.
Provides administrative functions for user management, analytics,
engagement tracking, and system monitoring.
Only accessible to users with admin privileges.
"""
import streamlit as st
from auth import load_users, require_admin, save_users, logout, log_user_activity
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone  # Update import to include timezone
import json  # Add this import for JSON handling
import os  # Add this import for file path handling

# Configure logging
logging.basicConfig(
    filename="admin_actions.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

require_admin()

def delete_user(username):
    """
    Deletes a user and logs the action.
    """
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        logging.info(f"Admin deleted user: {username}")
        return True
    logging.warning(f"Admin attempted to delete non-existent user: {username}")
    return False

def log_action(action):
    """
    Logs admin actions with timestamps in UTC.
    """
    with open("admin_logs.txt", "a") as log_file:
        log_file.write(f"{action} - {datetime.now(timezone.utc).isoformat()}\n")

def calculate_data_completeness(users):
    total_users = len(users)
    if total_users == 0:
        return 0

    complete_users = 0
    for username, user_data in users.items():
        user_file = os.path.join("user_data", f"{username}.json")
        if os.path.exists(user_file):
            try:
                with open(user_file, "r") as f:
                    transactions = json.load(f)
                    if transactions and len(transactions) > 0:
                        for transaction in transactions:
                            if all(key in transaction for key in ["Category", "Amount", "Date"]):
                                complete_users += 1
                                break
            except (json.JSONDecodeError, FileNotFoundError):
                pass
    
    return (complete_users / total_users) * 100 if total_users > 0 else 0

@st.cache_data
def get_recent_activity(users, days=7):
    recent_activity = {}
    cutoff_date = datetime.now() - timedelta(days=days)
    for username, user_data in users.items():
        activity_log = user_data.get("activity_log", [])
        recent_activity[username] = [
            log for log in activity_log if datetime.fromisoformat(log["timestamp"]) > cutoff_date
        ]
    return recent_activity

def admin_dashboard():
    st.title("Admin Panel")
    
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("🚪 Sign Out", type="primary", key="admin_signout"):
            logout()
            st.switch_page("app.py")
    
    st.subheader("User Management and Analytics")
    st.divider()
    
    users = load_users()  # Ensure proper indentation here
    st.write(f"**Total Registered Users:** {len(users)}")

    activity_data = {}
    total_logins = 0
    total_uploads = 0
    uploads_last_7_days = 0
    active_users_count = 0
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for username, user_data in users.items():
        if "activity_log" not in user_data:
            user_data["activity_log"] = []
        
        if user_data.get("last_login"):
            active_users_count += 1
            
        login_count = 0
        upload_count = 0
        recent_activity = False
        
        for log in user_data.get("activity_log", []):
            action = log.get("action", "")
            timestamp = datetime.fromisoformat(log.get("timestamp", datetime.now().isoformat()))
            
            if action == "login":
                login_count += 1
                total_logins += 1
                
            if action == "upload":
                upload_count += 1
                total_uploads += 1
                if timestamp > cutoff_date:
                    uploads_last_7_days += 1
                    recent_activity = True
        
        upload_count = user_data.get("upload_count", upload_count)
        login_count = user_data.get("login_count", login_count)
        
        activity_data[username] = {
            "login_count": login_count,
            "upload_count": upload_count,
            "recent_activity": recent_activity
        }
    
    active_sessions = st.session_state.get("active_sessions", [])
    st.write(f"**Active Users:** {active_users_count}")
    st.write(f"**Active Sessions:** {len(active_sessions)}")
    st.write("### Engagement Stats")

    engaged_users = sum(1 for data in activity_data.values() if data["recent_activity"])
    st.write(f"**Engaged Users (Last 7 Days):** {engaged_users}")
    st.write(f"**Uploads (Last 7 Days):** {uploads_last_7_days}")
    st.write(f"**Total Uploads (All Time):** {total_uploads}")
    st.write(f"**Total Logins (All Time):** {total_logins}")

    login_counts = {username: data["login_count"] for username, data in activity_data.items()}
    if any(count > 0 for count in login_counts.values()):
        st.write("### Login Frequency")
        login_df = pd.DataFrame.from_dict(login_counts, orient="index", columns=["Logins"])
        st.bar_chart(login_df)
    else:
        st.info("No login activity recorded yet.")

    if st.button("View Logs"):
        st.write("### Admin Logs")
        try:
            with open("admin_logs.txt", "r") as log_file:
                logs = log_file.readlines()
                st.text_area("Admin Logs", value="".join(logs), height=200)
        except FileNotFoundError:
            st.info("No logs available yet.")
            log_action("Admin viewed logs (no logs available)")

    roles = {"admin": 2, "user": 10}
    st.write("### User Roles")
    st.bar_chart(roles)

    completeness_score = calculate_data_completeness(users)
    st.write(f"**Data Completeness Score:** {completeness_score:.2f}%")

    st.write("### User Table")
    user_table = []
    for username, user_data in users.items():
        upload_logs = [log for log in user_data.get("activity_log", []) if log.get("action") == "upload"]
        last_upload = "Never"
        if upload_logs:
            last_upload_timestamp = max(datetime.fromisoformat(log["timestamp"]) for log in upload_logs)
            last_upload = last_upload_timestamp.strftime("%B %Y")
            
        uploads_this_month = sum(
            1 for log in upload_logs 
            if datetime.fromisoformat(log["timestamp"]).month == datetime.now().month
        )
        
        login_logs = [log for log in user_data.get("activity_log", []) if log.get("action") == "login"]
        last_login = "Never"
        if login_logs:
            last_login_timestamp = max(datetime.fromisoformat(log["timestamp"]) for log in login_logs)
            last_login = last_login_timestamp.strftime("%B %d, %Y")
        elif user_data.get("last_login"):
            try:
                last_login = datetime.fromisoformat(user_data["last_login"]).strftime("%B %d, %Y")
            except (ValueError, TypeError):
                last_login = "Never"
        
        user_table.append({
            "Username": username,
            "Role": user_data.get("role", "user"),
            "Last Login": last_login,
            "Last Upload": last_upload,
            "Uploads This Month": uploads_this_month,
            "Total Uploads": activity_data[username]["upload_count"],
            "Total Logins": activity_data[username]["login_count"]
        })
    
    st.dataframe(pd.DataFrame(user_table))
    
    st.write("### Inactive Accounts")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    inactive_users = []
    for username, user_data in users.items():
        last_activity = None
        if user_data.get("activity_log"):
            activity_timestamps = [datetime.fromisoformat(log["timestamp"]) for log in user_data["activity_log"]]
            if activity_timestamps:
                last_activity = max(activity_timestamps)
        if not last_activity and user_data.get("last_login"):
            last_activity = datetime.fromisoformat(user_data["last_login"])
        if not last_activity or last_activity < thirty_days_ago:
            inactive_users.append(username)
    
    if inactive_users:
        st.write("Inactive Users (Last 30 Days):")
        for user in inactive_users:
            st.write(f"- {user}")
    else:
        st.write("No inactive users found.")

    registration_dates = []
    for username, user_data in users.items():
        if user_data.get("registration_date"):
            try:
                reg_date = datetime.fromisoformat(user_data["registration_date"])
                registration_dates.append(reg_date)
            except (ValueError, TypeError):
                continue
    
    if registration_dates:
        registration_df = pd.DataFrame({"Date": registration_dates})
        registration_df = registration_df.sort_values("Date")
        registration_df["Cumulative Users"] = range(1, len(registration_df) + 1)
        st.write("### User Growth")
        chart = alt.Chart(registration_df).mark_line().encode(
            x='Date:T',
            y='Cumulative Users:Q'
        ).properties(
            title='User Growth Over Time'
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No registration dates available for user growth chart.")

    st.metric("Active Users", active_users_count)

    current_date = datetime.now().strftime('%Y-%m-%d')
    admin_stats_data = pd.DataFrame(user_table).to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Admin Stats",
        data=admin_stats_data,
        file_name=f"admin_stats_{current_date}.csv",
        mime="text/csv",
        key="admin_stats_download",
        on_click=lambda: log_action(f"Admin downloaded stats on {current_date}")
    )

if __name__ == "__main__":
    admin_dashboard()