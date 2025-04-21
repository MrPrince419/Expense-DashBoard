"""
Admin Panel for the Expense Tracker application.
Provides administrative functions for user management, analytics,
engagement tracking, and system monitoring.
Only accessible to users with admin privileges.
"""
import streamlit as st

# Set page config as the first Streamlit command
st.set_page_config(page_title="Admin Panel", layout="wide")

from auth import load_users, require_admin, save_users, logout, log_user_activity
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone
import json
import os
import altair as alt

logging.basicConfig(
    filename="admin_actions.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

st.write("### Admin Authentication Check")
if st.session_state.get("role") == "admin":
    st.success("✅ You are properly authenticated as an admin.")
else:
    st.error("❌ You don't have proper admin authentication.")
    st.info("To login as admin, use:\n- Email: admin@example.com\n- Password: Admin@123456\n\nPlease logout and use the Admin login option.")
    st.stop()

st.write(f"Debug - Session state: authenticated={st.session_state.get('authenticated')}, role={st.session_state.get('role')}")

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
    
    users = load_users()
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
    
    st.write("### Summary Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Users", active_users_count, 
                 help="Users who have logged in at least once")
    with col2:
        st.metric("Engaged Users", sum(1 for data in activity_data.values() if data["recent_activity"]),
                 help="Users who have uploaded data in the last 7 days")
    with col3:
        st.metric("Total Uploads", total_uploads,
                 help="All-time number of uploads across all users")
    with col4:
        st.metric("Active Sessions", len(st.session_state.get("active_sessions", [])),
                 help="Number of users currently logged in")
    
    st.write("### Engagement Statistics")
    st.info("Hover over any chart element to see detailed information.")
    
    login_counts = {username: data["login_count"] for username, data in activity_data.items()}
    if any(count > 0 for count in login_counts.values()):
        st.write("#### Login Frequency by User")
        login_df = pd.DataFrame({"User": login_counts.keys(), "Logins": login_counts.values()})
        login_df = login_df.sort_values("Logins", ascending=False)
        
        login_chart = alt.Chart(login_df).mark_bar().encode(
            x=alt.X('User:N', title='User', sort='-y'),
            y=alt.Y('Logins:Q', title='Number of Logins'),
            tooltip=['User', 'Logins'],
            color=alt.Color('Logins:Q', scale=alt.Scale(scheme='blues'))
        ).properties(
            height=300,
            title='User Login Frequency'
        ).interactive()
        
        st.altair_chart(login_chart, use_container_width=True)
    else:
        st.info("No login activity recorded yet.")
    
    st.write("#### User Role Distribution")
    role_counts = {}
    for user_data in users.values():
        role = user_data.get("role", "user")
        role_counts[role] = role_counts.get(role, 0) + 1
    
    role_df = pd.DataFrame({"Role": role_counts.keys(), "Count": role_counts.values()})
    
    role_chart = alt.Chart(role_df).mark_arc().encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field="Role", type="nominal", 
                       scale=alt.Scale(scheme='category10')),
        tooltip=["Role", "Count"]
    ).properties(
        height=300,
        title="User Roles Distribution"
    )
    
    st.altair_chart(role_chart, use_container_width=True)
    
    st.write("#### User Activity Timeline")
    
    all_activity = []
    for username, user_data in users.items():
        for log in user_data.get("activity_log", []):
            try:
                all_activity.append({
                    "User": username,
                    "Action": log.get("action", "unknown"),
                    "Date": datetime.fromisoformat(log.get("timestamp")).date(),
                    "Timestamp": log.get("timestamp")
                })
            except (ValueError, TypeError):
                pass
    
    if all_activity:
        activity_df = pd.DataFrame(all_activity)
        activity_df = activity_df.sort_values("Timestamp")
        
        timeline = alt.Chart(activity_df).mark_circle(size=100).encode(
            x=alt.X('Date:T', title='Date'),
            y=alt.Y('User:N', title='User'),
            color=alt.Color('Action:N', scale=alt.Scale(scheme='tableau10')),
            tooltip=['User', 'Action', 'Date:T']
        ).properties(
            height=300,
            title='User Activity Timeline'
        ).interactive()
        
        st.altair_chart(timeline, use_container_width=True)
    else:
        st.info("No user activity data available for timeline.")
    
    st.write("#### Data Quality Assessment")
    
    completeness_score = calculate_data_completeness(users)
    st.write(f"**Data Completeness Score:** {completeness_score:.2f}%")
    
    completion_source = pd.DataFrame([
        {"category": "Complete", "value": completeness_score},
        {"category": "Incomplete", "value": 100 - completeness_score}
    ])
    
    gauge = alt.Chart(completion_source).mark_arc().encode(
        theta=alt.Theta(field="value", type="quantitative", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color(
            field="category",
            type="nominal",
            scale=alt.Scale(domain=["Complete", "Incomplete"], 
                          range=["#28a745", "#f8f9fa"])
        ),
        tooltip=["category", "value"]
    ).properties(
        height=250,
        title="Data Completeness"
    )
    
    st.altair_chart(gauge, use_container_width=True)
    
    st.write("#### User Growth Over Time")
    
    registration_dates = []
    for username, user_data in users.items():
        if user_data.get("registration_date"):
            try:
                reg_date = datetime.fromisoformat(user_data["registration_date"])
                registration_dates.append({"User": username, "Date": reg_date})
            except (ValueError, TypeError):
                continue
    
    if registration_dates:
        registration_df = pd.DataFrame(registration_dates)
        registration_df = registration_df.sort_values("Date")
        
        dates_only = registration_df[["Date"]].copy()
        dates_only["count"] = 1
        dates_only = dates_only.sort_values("Date")
        dates_only["Cumulative Users"] = dates_only["count"].cumsum()
        
        chart = alt.Chart(dates_only).mark_line(point=True).encode(
            x=alt.X('Date:T', title='Registration Date'),
            y=alt.Y('Cumulative Users:Q', title='Total Users'),
            tooltip=['Date:T', 'Cumulative Users:Q']
        ).properties(
            height=300,
            title='User Growth Over Time'
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No registration dates available for user growth chart.")
    
    st.write("### User Table")
    
    user_table = []
    for username, user_data in users.items():
        upload_logs = [log for log in user_data.get("activity_log", []) if log.get("action") == "upload"]
        last_upload = "Never"
        if upload_logs:
            try:
                last_upload_timestamp = max(datetime.fromisoformat(log["timestamp"]) for log in upload_logs)
                last_upload = last_upload_timestamp.strftime("%B %d, %Y")
            except (ValueError, TypeError):
                last_upload = "Error parsing date"
        
        uploads_this_month = 0
        try:
            uploads_this_month = sum(
                1 for log in upload_logs 
                if datetime.fromisoformat(log["timestamp"]).month == datetime.now().month
            )
        except (ValueError, TypeError):
            pass
        
        login_logs = [log for log in user_data.get("activity_log", []) if log.get("action") == "login"]
        last_login = "Never"
        if login_logs:
            try:
                last_login_timestamp = max(datetime.fromisoformat(log["timestamp"]) for log in login_logs)
                last_login = last_login_timestamp.strftime("%B %d, %Y")
            except (ValueError, TypeError):
                last_login = "Error parsing date"
        elif user_data.get("last_login"):
            try:
                last_login = datetime.fromisoformat(user_data["last_login"]).strftime("%B %d, %Y")
            except (ValueError, TypeError):
                last_login = "Error parsing date"
        
        user_table.append({
            "Username": username,
            "Role": user_data.get("role", "user"),
            "Last Login": last_login,
            "Last Upload": last_upload,
            "Uploads This Month": uploads_this_month,
            "Total Uploads": activity_data.get(username, {}).get("upload_count", 0),
            "Total Logins": activity_data.get(username, {}).get("login_count", 0),
            "Email": user_data.get("email", "Unknown")
        })
    
    user_df = pd.DataFrame(user_table)
    
    filter_cols = st.columns(3)
    with filter_cols[0]:
        filter_role = st.selectbox("Filter by Role", ["All"] + list(role_counts.keys()))
    with filter_cols[1]:
        has_uploads = st.checkbox("Only Users with Uploads")
    with filter_cols[2]:
        sort_by = st.selectbox("Sort By", 
                              ["Username", "Role", "Total Uploads", "Total Logins"])
    
    filtered_df = user_df
    if filter_role != "All":
        filtered_df = filtered_df[filtered_df["Role"] == filter_role]
    if has_uploads:
        filtered_df = filtered_df[filtered_df["Total Uploads"] > 0]
    
    filtered_df = filtered_df.sort_values(sort_by, ascending=False)
    
    st.dataframe(filtered_df, use_container_width=True)
    
    st.write("### Inactive Accounts")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    inactive_users = []
    
    for username, user_data in users.items():
        last_activity = None
        if user_data.get("activity_log"):
            try:
                activity_timestamps = [datetime.fromisoformat(log["timestamp"]) for log in user_data["activity_log"]]
                if activity_timestamps:
                    last_activity = max(activity_timestamps)
            except (ValueError, TypeError):
                pass
                
        if not last_activity and user_data.get("last_login"):
            try:
                last_activity = datetime.fromisoformat(user_data["last_login"])
            except (ValueError, TypeError):
                pass
                
        if not last_activity or last_activity < thirty_days_ago:
            inactive_users.append({
                "Username": username,
                "Email": user_data.get("email", "Unknown"),
                "Last Activity": last_activity.strftime("%B %d, %Y") if last_activity else "Never"
            })
    
    if inactive_users:
        st.write(f"Found {len(inactive_users)} users with no activity in the last 30 days:")
        inactive_df = pd.DataFrame(inactive_users)
        st.dataframe(inactive_df, use_container_width=True)
    else:
        st.write("No inactive users found.")

    st.write("### Admin Activity Logs")
    if st.button("View Admin Logs"):
        try:
            with open("admin_logs.txt", "r") as log_file:
                logs = log_file.readlines()
                st.text_area("Admin Logs", value="".join(logs), height=200)
        except FileNotFoundError:
            st.info("No admin logs available yet.")
            log_action("Admin viewed logs (no logs available)")

    st.write("### Export Data")
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    col1, col2 = st.columns(2)
    with col1:
        admin_stats_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download User Statistics",
            data=admin_stats_data,
            file_name=f"user_stats_{current_date}.csv",
            mime="text/csv",
            key="user_stats_download",
            on_click=lambda: log_action(f"Admin downloaded user stats on {current_date}")
        )
    
    with col2:
        activity_data_export = pd.DataFrame(all_activity).to_csv(index=False).encode('utf-8') if all_activity else "No activity data".encode('utf-8')
        st.download_button(
            label="📥 Download Activity Data",
            data=activity_data_export,
            file_name=f"activity_data_{current_date}.csv",
            mime="text/csv",
            key="activity_download",
            on_click=lambda: log_action(f"Admin downloaded activity data on {current_date}")
        )

if __name__ == "__main__":
    admin_dashboard()