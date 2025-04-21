"""
Dashboard page for the Expense Tracker application.
Visualizes financial data with analytics, charts, and insights.
Allows users to edit transactions and view spending patterns.
"""
import streamlit as st
import pandas as pd
import plotly.express as px  # Add this import for visualizations
from auth import restrict_access
from utils import load_user_data, save_user_data

# Ensure only authenticated users can access this page
restrict_access()

# Additional authentication check
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("Please login to view this page.")
    st.stop()

if "user" not in st.session_state:
    st.error("Please login to view this page.")
    st.stop()

# Navigation bar
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("🏠 Home"):
        st.switch_page("app.py")
with col2:
    if st.button("📤 Upload"):
        st.switch_page("pages/1_Upload.py")
with col3:
    if st.button("🚪 Sign Out"):
        from auth import logout
        logout()
        st.switch_page("app.py")

st.divider()

# Function to ensure required columns exist
def ensure_columns_exist(data, required_columns):
    """
    Ensure all required columns exist in the DataFrame.
    Adds missing columns with default values.
    """
    for col in required_columns:
        if col not in data.columns:
            data[col] = "Unknown" if col != "Amount" else 0.0
    return data

# Load the current user's data
username = st.session_state["user"]
data = load_user_data(username)

# Ensure required columns exist
required_columns = ["Date", "Amount", "Name", "Type", "Category"]
data = ensure_columns_exist(data, required_columns)

# Check if there's data to display
if data.empty:
    st.warning("No data uploaded yet. Please upload your financial data on the Upload page.")
    st.stop()

st.title("Dashboard")

st.subheader("Key Metrics")
def calculate_metrics():
    """
    Calculate key financial metrics from transaction data.
    Handles missing or inconsistent data gracefully.
    Returns:
        tuple: (total_income, total_expenses, net_savings)
    """
    transactions = st.session_state.get("transactions", pd.DataFrame())
    if transactions.empty or "Type" not in transactions.columns or "Amount" not in transactions.columns:
        return 0, 0, 0

    # Fill missing values in 'Type' and 'Amount' columns
    transactions["Type"] = transactions["Type"].fillna("Unknown")
    transactions["Amount"] = transactions["Amount"].fillna(0.0)

    grouped = transactions.groupby("Type")["Amount"].sum()
    total_income = grouped.get("Income", 0)
    total_expenses = grouped.get("Expense", 0)
    net_savings = total_income - total_expenses
    return total_income, total_expenses, net_savings

# Display key financial metrics
col1, col2, col3 = st.columns(3)
total_income, total_expenses, net_savings = calculate_metrics()

with col1:
    income_metric = st.metric("Total Income", f"${total_income:,.2f}")
with col2:
    expense_metric = st.metric("Total Expenses", f"${total_expenses:,.2f}")
with col3:
    savings_metric = st.metric("Net Savings", f"${net_savings:,.2f}", delta_color="inverse")

# Transaction editor
st.subheader("Transactions")
edited_transactions = st.data_editor(
    st.session_state["transactions"],
    num_rows="dynamic",
    key="transaction_editor",
    on_change=None
)

# Handle changes to transactions and save them
if not edited_transactions.equals(st.session_state["transactions"]):
    # Update the stored transactions with edited values
    st.session_state["transactions"] = edited_transactions.copy()
    
    # Recalculate metrics based on edited data
    total_income, total_expenses, net_savings = calculate_metrics()
    st.rerun()

    # Save the updated transactions to user data file
    save_user_data(username, st.session_state["transactions"])

# Basic insights section
st.subheader("Basic Insights")
if "transactions" in st.session_state:
    transactions = st.session_state["transactions"]

    # Total transaction count
    st.write("### Total Transactions")
    total_transactions = len(transactions)
    st.metric("Total Transactions", total_transactions)

    # Average transaction amount
    st.write("### Average Transaction Amount")
    if "Amount" in transactions.columns:
        avg_transaction = transactions["Amount"].mean()
        st.metric("Average Transaction Amount", f"${avg_transaction:,.2f}")
    else:
        st.info("Please ensure your data has an Amount column.")

    # Most frequent merchant
    st.write("### Most Frequent Merchant")
    if "Name" in transactions.columns:
        most_frequent_merchant = transactions["Name"].mode()[0]
        st.metric("Most Frequent Merchant", most_frequent_merchant)
    else:
        st.info("Please ensure your data has a Name column.")

# Visualizations section
st.subheader("Visualizations")

# Income vs Expense chart
st.write("### Income vs Expense")
if "Type" in st.session_state["transactions"].columns and "Date" in st.session_state["transactions"].columns:
    # Aggregate data by month for large datasets
    transactions = st.session_state["transactions"]
    transactions["Date"] = pd.to_datetime(transactions["Date"])
    aggregated_data = transactions.groupby([transactions["Date"].dt.to_period("M"), "Type"])["Amount"].sum().reset_index()
    aggregated_data["Date"] = aggregated_data["Date"].astype(str)

    line_chart = px.line(
        aggregated_data,
        x="Date",
        y="Amount",
        color="Type",
        title="Income vs Expense Over Time"
    )
    st.plotly_chart(line_chart, use_container_width=True)
else:
    st.info("Please ensure your data has Date, Amount, and Type columns.")

# Spending category breakdown
st.write("### Spending Breakdown")
if "Type" in st.session_state["transactions"].columns and "Category" in st.session_state["transactions"].columns:
    # Filter for expense transactions only
    expense_data = st.session_state["transactions"].query("Type == 'Expense'")
    if not expense_data.empty:
        pie_chart = px.pie(
            expense_data,
            names="Category",
            values="Amount",
            title="Spending Breakdown by Category"
        )
        st.plotly_chart(pie_chart, use_container_width=True)
    else:
        st.info("No expense data available to display.")
else:
    st.info("Please ensure your data has Type and Category columns.")

# Advanced insights section
st.subheader("Advanced Insights")
if "transactions" in st.session_state:
    transactions = st.session_state["transactions"]

    # Monthly spending trends
    st.write("### Monthly Trends")
    if "Date" in transactions.columns and "Amount" in transactions.columns:
        # Convert date column to period for monthly grouping
        transactions["Month"] = pd.to_datetime(transactions["Date"]).dt.to_period("M")
        transactions["Month"] = transactions["Month"].astype(str)
        monthly_summary = transactions.groupby("Month")["Amount"].sum().reset_index()
        
        # Create monthly bar chart
        monthly_chart = px.bar(
            monthly_summary,
            x="Month",
            y="Amount",
            title="Monthly Spending Trends",
            labels={"Amount": "Total Amount", "Month": "Month"}
        )
        st.plotly_chart(monthly_chart, use_container_width=True)
    else:
        st.info("Please ensure your data has Date and Amount columns.")

    # Top spending categories
    st.write("### Top Spending Categories")
    if "Category" in transactions.columns and "Amount" in transactions.columns:
        # Group by category and get top 5
        category_summary = transactions.groupby("Category")["Amount"].sum().reset_index()
        category_summary = category_summary.sort_values(by="Amount", ascending=False).head(5)
        
        # Create category bar chart
        category_chart = px.bar(
            category_summary,
            x="Category",
            y="Amount",
            title="Top 5 Spending Categories",
            labels={"Amount": "Total Amount", "Category": "Category"}
        )
        st.plotly_chart(category_chart, use_container_width=True)
    else:
        st.info("Please ensure your data has Category and Amount columns.")

    # Spending anomalies detection
    st.write("### Anomalies in Spending")
    with st.expander("View Anomalies in Spending"):
        if "Amount" in transactions.columns:
            # Calculate statistical outliers (2 standard deviations from mean)
            mean_amount = transactions["Amount"].mean()
            std_dev = transactions["Amount"].std()
            anomalies = transactions[(transactions["Amount"] > mean_amount + 2 * std_dev) | 
                                   (transactions["Amount"] < mean_amount - 2 * std_dev)]
            
            # Display anomalies if found
            if not anomalies.empty:
                st.warning("Anomalies detected in your spending data:")
                st.dataframe(anomalies)
            else:
                st.success("No anomalies detected in your spending data.")
        else:
            st.info("Please ensure your data has an Amount column.")