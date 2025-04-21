"""
Dashboard page for the Expense Tracker application.
Provides visualizations and insights based on transaction data.
Adapts to available data fields with graceful fallbacks.
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from auth import restrict_access
from utils import get_transactions
import plotly.express as px  # Import plotly for interactive charts

# Set the page configuration
st.set_page_config(page_title="Expense Dashboard", layout="wide")

# Custom styling
st.markdown("""
<style>
    .metric-card {
        border: 1px solid #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .small-font {
        font-size: 0.8rem;
    }
    .chart-container {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Ensure only authenticated users can access this page
restrict_access()

# Additional authentication check
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("Please login to view this page.")
    st.stop()

if "user" not in st.session_state:
    st.error("Please login to view this page.")
    st.stop()

# When returning to Dashboard, ensure transactions are loaded
if "user" in st.session_state:
    username = st.session_state["user"]
    
    # Get transaction data - ensure real-time sync with Upload page
    data = get_transactions()
    
    # Add a debug message to show data is preserved
    if not data.empty:
        st.success(f"Loaded {len(data)} transactions from your account")

# Display the current user
st.markdown(
    f"<div><strong>👤 {st.session_state['user']}</strong></div><hr>",
    unsafe_allow_html=True
)

# Get transaction data - ensure real-time sync with Upload page
data = get_transactions()

# Handle empty data gracefully
if data.empty:
    st.info("🔍 No transaction data found. Upload some data to view insights!")
    st.markdown("### Quick Start")
    st.markdown("""
    1. Go to the Upload page to add your financial data
    2. Return here to see your personalized dashboard
    3. Explore insights about your spending patterns
    """)
    st.stop()

# Process and ensure required columns exist
st.title("📊 Financial Dashboard")

# Ensure required columns exist (CHANGED: more resilient approach)
required_columns = ["Date", "Amount", "Name"]
optional_columns = ["Type", "Category"]

# Check for missing required columns
missing_required = [col for col in required_columns if col not in data.columns]
if missing_required:
    st.warning(f"Missing required columns: {', '.join(missing_required)}. Some features may not work correctly.")
    for col in missing_required:
        if col == "Date":
            data[col] = pd.to_datetime("today")
        elif col == "Amount":
            data[col] = 0.0
        else:
            data[col] = "Unknown"

# Add optional columns with default values if missing
for col in optional_columns:
    if col not in data.columns:
        data[col] = "Unknown"

# Ensure Amount is numeric
data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce").fillna(0)

# Ensure Date is datetime
if "Date" in data.columns:
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    
    # Add date filtering
    with st.sidebar:
        st.header("Dashboard Filters")
        date_min = data["Date"].min()
        date_max = data["Date"].max()
        
        # Default to last 30 days if we have enough data
        default_start = max(date_min, date_max - timedelta(days=30))
        
        date_range = st.date_input(
            "Filter by Date Range", 
            value=[default_start.date(), date_max.date()],
            min_value=date_min.date(),
            max_value=date_max.date()
        )
        
        if len(date_range) == 2:
            start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            filtered_data = data[(data["Date"] >= start) & (data["Date"] <= end)]
            if not filtered_data.empty:
                data = filtered_data
                st.success(f"Showing data from {start.date()} to {end.date()}")
            else:
                st.warning("No data in selected date range. Showing all data.")

# Create two columns for top metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 💰 Total Spending")
    total_spent = data["Amount"].sum()
    st.metric("Total", f"${total_spent:,.2f}")
    
    avg_transaction = data["Amount"].mean()
    st.caption(f"Average Transaction: ${avg_transaction:,.2f}")

with col2:
    st.markdown("### 🔍 Largest Transaction")
    if "Amount" in data.columns and not data.empty:
        biggest_idx = data["Amount"].idxmax()
        biggest = data.loc[biggest_idx]
        st.metric("Largest Amount", f"${biggest['Amount']:,.2f}")
        st.caption(f"Merchant: {biggest.get('Name', 'Unknown')} | Date: {biggest.get('Date', 'Unknown').strftime('%Y-%m-%d') if isinstance(biggest.get('Date', 'Unknown'), pd.Timestamp) else biggest.get('Date', 'Unknown')}")

with col3:
    st.markdown("### 📊 Transaction Overview")
    transaction_count = len(data)
    st.metric("Total Transactions", f"{transaction_count:,}")
    
    # Category diversity (if available)
    if "Category" in data.columns and data["Category"].nunique() > 1:
        category_count = data["Category"].nunique()
        st.caption(f"Categories: {category_count} unique")
    else:
        st.caption("Add a 'Category' column to track spending categories")

# Spending Consistency Score
st.markdown("### 📈 Spending Patterns")
col1, col2 = st.columns(2)

with col1:
    if "Date" in data.columns and len(data) > 1:
        try:
            # Group by date and calculate daily totals
            daily_totals = data.groupby(data["Date"].dt.date)["Amount"].sum()
            
            if len(daily_totals) > 1:
                # Calculate coefficient of variation (normalized std dev)
                mean_spending = daily_totals.mean()
                std_spending = daily_totals.std()
                variability = (std_spending / mean_spending) if mean_spending > 0 else 0
                
                # Convert to consistency score (100 = perfectly consistent, 0 = highly variable)
                consistency = max(0, min(100, 100 - (variability * 100)))
                
                st.metric("Spending Consistency", f"{consistency:.1f}/100")
                
                if consistency > 80:
                    st.caption("Your spending is very consistent day-to-day")
                elif consistency > 50:
                    st.caption("Your spending has moderate variability")
                else:
                    st.caption("Your spending varies significantly day-to-day")
            else:
                st.caption("Need more daily data to calculate consistency")
        except Exception as e:
            st.caption("Couldn't calculate consistency. Check your date format.")
    else:
        st.caption("Add more transactions with dates to see consistency metrics")

with col2:
    if "Category" in data.columns and data["Category"].nunique() > 1:
        # Category diversity
        diversity = data["Category"].nunique()
        top_category = data.groupby("Category")["Amount"].sum().idxmax()
        top_category_percent = (data[data["Category"] == top_category]["Amount"].sum() / total_spent) * 100
        
        st.metric("Top Category", f"{top_category}")
        st.caption(f"Represents {top_category_percent:.1f}% of your total spending")
    else:
        st.info("Add a 'Category' column to unlock category insights")

# Transaction Over Time visualization
st.markdown("### 📅 Transactions Over Time")

if "Date" in data.columns and not data.empty:
    # Group by day and sum amounts
    time_data = data.copy()
    time_data["Date"] = pd.to_datetime(time_data["Date"])
    daily_totals = time_data.groupby(time_data["Date"].dt.date)["Amount"].sum().reset_index()
    
    if len(daily_totals) > 1:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(daily_totals["Date"], daily_totals["Amount"], marker='o', linewidth=2, markersize=6)
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount ($)")
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()  # Rotate date labels
        
        st.pyplot(fig)
    else:
        st.info("Not enough daily transaction data to show a time trend.")
else:
    st.info("Add dates to your transactions to see spending over time.")

# Income vs Expense Analysis (if Type column exists)
if "Type" in data.columns and data["Type"].nunique() > 1:
    st.markdown("### 💸 Income vs Expenses")
    
    # Identify income and expense categories (common values)
    income_keywords = ["income", "revenue", "salary", "deposit", "credit"]
    expense_keywords = ["expense", "cost", "payment", "debit", "purchase"]
    
    # Clean up Type categories and standardize
    data["Type"] = data["Type"].astype(str).str.lower().str.strip()
    
    # Function to categorize Types
    def categorize_type(type_value):
        if any(keyword in type_value for keyword in income_keywords):
            return "Income"
        elif any(keyword in type_value for keyword in expense_keywords):
            return "Expense"
        else:
            return type_value.title()
    
    data["TypeCategory"] = data["Type"].apply(categorize_type)
    
    # Create income/expense chart
    type_data = data.groupby("TypeCategory")["Amount"].sum().reset_index()
    
    if len(type_data) > 1:
        fig, ax = plt.subplots(figsize=(8, 4))
        sns.barplot(x="TypeCategory", y="Amount", data=type_data, ax=ax)
        ax.set_xlabel("")
        ax.set_ylabel("Amount ($)")
        
        st.pyplot(fig)
        
        # Calculate income-expense balance
        if "Income" in type_data["TypeCategory"].values and "Expense" in type_data["TypeCategory"].values:
            income = type_data.loc[type_data["TypeCategory"] == "Income", "Amount"].values[0]
            expense = type_data.loc[type_data["TypeCategory"] == "Expense", "Amount"].values[0]
            balance = income - expense
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Income", f"${income:,.2f}")
            with col2:
                st.metric("Expenses", f"${expense:,.2f}")
            with col3:
                st.metric("Balance", f"${balance:,.2f}", delta=f"{balance/income*100:.1f}% of income" if income > 0 else "N/A")
    else:
        st.info("Add more Type values to see Income vs Expense analysis")
else:
    st.info("Add a 'Type' column with values like 'Income' and 'Expense' to unlock Income/Expense insights")

# Category breakdown visualizations
if "Category" in data.columns and data["Category"].nunique() > 1:
    st.markdown("### 📈 Spending by Category")
    
    category_data = data.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
    
    # 🔄 Pre-filter negative values to avoid crashes across all visualizations
    category_data = category_data[category_data["Amount"] > 0]
    
    # Only proceed if we have positive data to show
    if not category_data.empty:
        # Display pie chart and bar chart stacked vertically
        
        # Interactive Plotly Pie Chart with tooltips
        st.subheader("🥧 Category Distribution")
        
        if len(category_data) > 5:
            # Limit to top 5 categories and group others
            top_5 = category_data.head(5)
            others_sum = category_data.iloc[5:]["Amount"].sum()
            if others_sum > 0:  # Only add "Others" if sum is positive
                top_5 = pd.concat([top_5, pd.DataFrame({"Category": ["Others"], "Amount": [others_sum]})])
            
            pie_data = top_5.copy()
            title = "Top 5 Categories Distribution"
        else:
            pie_data = category_data.copy()
            title = "Category Distribution"
        
        # Create interactive pie chart with Plotly
        fig = px.pie(
            pie_data, 
            names='Category', 
            values='Amount',
            title=title,
            hole=0.3,  # Creates a donut chart for better readability
            color_discrete_sequence=px.colors.qualitative.Plotly  # Attractive color scheme
        )
        
        # Update with more readable tooltips and remove text inside slices
        fig.update_traces(
            textinfo='none',  # Remove text inside the slices
            hoverinfo='label+percent+value',
            hovertemplate='<b>%{label}</b><br>Amount: $%{value:.2f}<br>Percentage: %{percent}<extra></extra>'
        )
        
        # Improve legend layout
        fig.update_layout(
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="right",
                x=1.1
            )
        )
        
        # Display the interactive chart
        st.plotly_chart(fig, use_container_width=True)
        
        # Add spacing between charts
        st.write("")
        
        # Bar chart of all categories - now full width
        st.subheader("📊 Category Breakdown (Bar Chart)")
        fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
        plot_data = category_data.head(10) if len(category_data) > 10 else category_data
        
        if not plot_data.empty:
            bars = sns.barplot(x="Amount", y="Category", data=plot_data, ax=ax_bar)
            ax_bar.set_xlabel("Amount ($)", fontsize=12)
            ax_bar.set_ylabel("Category", fontsize=12)
            ax_bar.tick_params(labelsize=10)
            
            # Add value labels to the bars
            for i, bar in enumerate(bars.patches):
                width = bar.get_width()
                ax_bar.text(width + 5, bar.get_y() + bar.get_height()/2, 
                          f"${width:,.2f}", ha='left', va='center', fontsize=10)
                
            ax_bar.set_title("Spending by Category", fontsize=14)
        else:
            ax_bar.text(0.5, 0.5, 'No positive data to plot', ha='center', va='center')
            ax_bar.axis('off')
            
        st.pyplot(fig_bar)
        
        if len(category_data) > 10:
            st.caption("Showing top 10 categories by amount")
    else:
        st.info("No positive spending amounts to visualize by category. Try adding transactions with positive amounts.")
else:
    st.info("Add a 'Category' column to visualize spending by category")

# Advanced insights and recommendations
st.markdown("### 🧠 Smart Insights")

insights = []

# Check for consistent high spend categories
if "Category" in data.columns and "Date" in data.columns and data["Category"].nunique() > 1:
    try:
        # Get categories with spending in multiple time periods
        data["Month"] = data["Date"].dt.to_period("M")
        category_frequency = data.groupby("Category")["Month"].nunique()
        consistent_categories = category_frequency[category_frequency > 1].index.tolist()
        
        if consistent_categories:
            insights.append(f"🔄 You consistently spend on {', '.join(consistent_categories[:3])}{'...' if len(consistent_categories) > 3 else ''}")
    except:
        pass

# Check for unusual large transactions
if "Amount" in data.columns and len(data) > 5:
    try:
        mean_amount = data["Amount"].mean()
        std_amount = data["Amount"].std()
        threshold = mean_amount + (2 * std_amount)
        
        unusual = data[data["Amount"] > threshold]
        if not unusual.empty:
            unusual_count = len(unusual)
            insights.append(f"⚠️ Found {unusual_count} unusually large transactions (>${threshold:.2f}+)")
    except:
        pass

# Check spending acceleration/deceleration if we have dates
if "Date" in data.columns and "Amount" in data.columns and len(data) > 10:
    try:
        # Split data into two time periods
        data = data.sort_values("Date")
        half_point = len(data) // 2
        first_half = data.iloc[:half_point]
        second_half = data.iloc[half_point:]
        
        first_total = first_half["Amount"].sum()
        second_total = second_half["Amount"].sum()
        
        change_pct = ((second_total - first_total) / first_total) * 100
        
        if abs(change_pct) > 20:
            direction = "increased" if change_pct > 0 else "decreased"
            insights.append(f"📈 Your spending has {direction} by {abs(change_pct):.1f}% recently")
    except:
        pass

# Display insights
if insights:
    for insight in insights:
        st.markdown(f"- {insight}")
else:
    st.caption("Add more transaction data to unlock smart insights")

# Recommendations based on data
st.markdown("### 💡 Recommendations")

recommendations = []

# Basic recommendations
recommendations.append("🔍 Categorize all transactions to get better insights")

# Budget recommendation if we have category data
if "Category" in data.columns and data["Category"].nunique() > 1:
    top_category = data.groupby("Category")["Amount"].sum().idxmax()
    recommendations.append(f"💰 Consider setting a budget for your highest spend category: {top_category}")

# Consistency recommendation if we have date data
if "Date" in data.columns and len(data) > 10:
    recommendations.append("📆 Set up regular payment tracking to improve your financial visibility")

# Display recommendations
if recommendations:
    for i, recommendation in enumerate(recommendations[:3], 1):
        st.markdown(f"**{i}.** {recommendation}")
else:
    st.caption("Add more transaction data to unlock personalized recommendations")

# Footer
st.markdown("---")
st.caption("💡 Tip: Upload more detailed transaction data to get even better insights and visualizations")