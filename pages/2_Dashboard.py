import streamlit as st
import pandas as pd
import plotly.express as px
from auth import restrict_access
from utils import load_user_data, save_user_data

restrict_access()

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("Please login to view this page.")
    st.stop()

if "user" not in st.session_state:
    st.error("Please login to view this page.")
    st.stop()

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

username = st.session_state["user"]
data = load_user_data(username)

if "transactions" not in st.session_state:
    st.warning("No data uploaded yet. Please upload your financial data on the Upload page.")
    st.stop()

st.title("Dashboard")

st.subheader("Key Metrics")
def calculate_metrics():
    if "Type" not in st.session_state["transactions"].columns:
        return 0, 0, 0
        
    total_income = st.session_state["transactions"].query("Type == 'Income'")["Amount"].sum()
    total_expenses = st.session_state["transactions"].query("Type == 'Expense'")["Amount"].sum()
    net_savings = total_income - total_expenses
    return total_income, total_expenses, net_savings

col1, col2, col3 = st.columns(3)
total_income, total_expenses, net_savings = calculate_metrics()

with col1:
    income_metric = st.metric("Total Income", f"${total_income:,.2f}")
with col2:
    expense_metric = st.metric("Total Expenses", f"${total_expenses:,.2f}")
with col3:
    savings_metric = st.metric("Net Savings", f"${net_savings:,.2f}", delta_color="inverse")

st.subheader("Transactions")
edited_transactions = st.data_editor(
    st.session_state["transactions"],
    num_rows="dynamic",
    key="transaction_editor",
    on_change=None
)

if not edited_transactions.equals(st.session_state["transactions"]):
    st.session_state["transactions"] = edited_transactions.copy()
    
    total_income, total_expenses, net_savings = calculate_metrics()
    st.rerun()

    save_user_data(username, st.session_state["transactions"])

st.subheader("Basic Insights")
if "transactions" in st.session_state:
    transactions = st.session_state["transactions"]

    st.write("### Total Transactions")
    total_transactions = len(transactions)
    st.metric("Total Transactions", total_transactions)

    st.write("### Average Transaction Amount")
    if "Amount" in transactions.columns:
        avg_transaction = transactions["Amount"].mean()
        st.metric("Average Transaction Amount", f"${avg_transaction:,.2f}")
    else:
        st.info("Please ensure your data has an Amount column.")

    st.write("### Most Frequent Merchant")
    if "Name" in transactions.columns:
        most_frequent_merchant = transactions["Name"].mode()[0]
        st.metric("Most Frequent Merchant", most_frequent_merchant)
    else:
        st.info("Please ensure your data has a Name column.")

st.subheader("Visualizations")

st.write("### Income vs Expense")
if "Type" in st.session_state["transactions"].columns and "Date" in st.session_state["transactions"].columns:
    line_chart = px.line(
        st.session_state["transactions"],
        x="Date",
        y="Amount",
        color="Type",
        title="Income vs Expense Over Time"
    )
    st.plotly_chart(line_chart, use_container_width=True)
else:
    st.info("Please ensure your data has Date, Amount, and Type columns.")

st.write("### Spending Breakdown")
if "Type" in st.session_state["transactions"].columns and "Category" in st.session_state["transactions"].columns:
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

st.subheader("Advanced Insights")
if "transactions" in st.session_state:
    transactions = st.session_state["transactions"]

    st.write("### Monthly Trends")
    if "Date" in transactions.columns and "Amount" in transactions.columns:
        transactions["Month"] = pd.to_datetime(transactions["Date"]).dt.to_period("M")
        transactions["Month"] = transactions["Month"].astype(str)
        monthly_summary = transactions.groupby("Month")["Amount"].sum().reset_index()
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

    st.write("### Top Spending Categories")
    if "Category" in transactions.columns and "Amount" in transactions.columns:
        category_summary = transactions.groupby("Category")["Amount"].sum().reset_index()
        category_summary = category_summary.sort_values(by="Amount", ascending=False).head(5)
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

    st.write("### Anomalies in Spending")
    with st.expander("View Anomalies in Spending"):
        if "Amount" in transactions.columns:
            mean_amount = transactions["Amount"].mean()
            std_dev = transactions["Amount"].std()
            anomalies = transactions[(transactions["Amount"] > mean_amount + 2 * std_dev) | (transactions["Amount"] < mean_amount - 2 * std_dev)]
            if not anomalies.empty:
                st.warning("Anomalies detected in your spending data:")
                st.dataframe(anomalies)
            else:
                st.success("No anomalies detected in your spending data.")
        else:
            st.info("Please ensure your data has an Amount column.")