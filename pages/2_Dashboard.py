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
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted #ccc;
        cursor: help;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)

restrict_access()

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("Please login to view this page.")
    st.stop()

if "user" not in st.session_state:
    st.error("Please login to view this page.")
    st.stop()

# Only get transactions once
username = st.session_state["user"]
data = get_transactions()

# Display welcome message with transaction count
if not data.empty:
    st.success(f"Loaded {len(data)} transactions from your account")

st.markdown(
    f"<div><strong>👤 {st.session_state['user']}</strong></div><hr>",
    unsafe_allow_html=True
)

if data.empty:
    st.info("🔍 No transaction data found. Upload some data to view insights!")
    st.markdown("### Quick Start")
    st.markdown("""
    1. Go to the Upload page to add your financial data
    2. Return here to see your personalized dashboard
    3. Explore insights about your spending patterns
    """)
    st.stop()

st.title("📊 Financial Dashboard")

# Ensure required columns exist - do this before filtering
required_columns = ["Date", "Amount", "Name"]
optional_columns = ["Type", "Category"]

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

# Add optional columns if needed
for col in optional_columns:
    if col not in data.columns:
        if col == "Type":
            data[col] = "Expense"
        else:
            data[col] = "Unknown"

# Convert data types BEFORE filtering
data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce").fillna(0)
data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

# Apply date filtering early
with st.sidebar:
    st.header("Dashboard Filters")
    date_min = data["Date"].min()
    date_max = data["Date"].max()
    
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
            data = filtered_data  # Override data with filtered data
            st.success(f"Showing data from {start.date()} to {end.date()}")
        else:
            st.warning("No data in selected date range. Showing all data.")

# Pre-process Type information
if "Type" in data.columns:
    # Using proper .loc[] to avoid SettingWithCopyWarning
    data_copy = data.copy()
    data_copy.loc[:, "Type"] = data_copy["Type"].astype(str).str.lower().str.strip()
    
    # Define helper for categorizing types
    def categorize_type(type_value):
        income_keywords = ["income", "revenue", "salary", "deposit", "credit"]
        expense_keywords = ["expense", "cost", "payment", "debit", "purchase"]
        
        if any(keyword in type_value for keyword in income_keywords):
            return "Income"
        elif any(keyword in type_value for keyword in expense_keywords):
            return "Expense"
        else:
            return type_value.title()
    
    data_copy.loc[:, "TypeCategory"] = data_copy["Type"].apply(categorize_type)
    data = data_copy
    
    # Pre-calculate income vs expense metrics
    type_data = data.groupby("TypeCategory")["Amount"].sum().reset_index()
    income_amount = type_data.loc[type_data["TypeCategory"] == "Income", "Amount"].sum() if "Income" in type_data["TypeCategory"].values else 0
    expense_amount = type_data.loc[type_data["TypeCategory"] == "Expense", "Amount"].sum() if "Expense" in type_data["TypeCategory"].values else 0
    balance = income_amount - expense_amount

# Calculate key metrics once and reuse them
transaction_count = len(data)
total_spent = data["Amount"].sum()
avg_transaction = data["Amount"].mean() if transaction_count > 0 else 0

# Display financial summary at the top
if "Type" in data.columns and data["TypeCategory"].nunique() > 1 and "Income" in data["TypeCategory"].values:
    st.markdown("### 💰 Financial Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Income", f"${income_amount:,.2f}")
    with col2:
        st.metric("Expenses", f"${expense_amount:,.2f}")
    with col3:
        st.metric("Balance", f"${balance:,.2f}", 
                 delta=f"{balance/income_amount*100:.1f}% of income" if income_amount > 0 else "N/A")
else:
    # Display top metrics without Income/Expense breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 💰 Total Spending")
        st.metric("Total", f"${total_spent:,.2f}")
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
        st.metric("Total Transactions", f"{transaction_count:,}")
        
        if "Category" in data.columns and data["Category"].nunique() > 1:
            category_count = data["Category"].nunique()
            st.caption(f"Categories: {category_count} unique")
        else:
            st.caption("Add a 'Category' column to track spending categories")

st.markdown("### 📈 Spending Patterns")
col1, col2 = st.columns(2)

with col1:
    if "Date" in data.columns and len(data) > 1:
        try:
            # Change from daily to weekly spending consistency
            # Group by week instead of by day for more stable consistency metrics
            data['Week'] = data['Date'].dt.isocalendar().week
            data['Year'] = data['Date'].dt.isocalendar().year
            data['YearWeek'] = data['Year'].astype(str) + '-' + data['Week'].astype(str)
            
            weekly_totals = data.groupby('YearWeek')["Amount"].sum()
            
            if len(weekly_totals) > 1:
                mean_spending = weekly_totals.mean()
                std_spending = weekly_totals.std()
                variability = (std_spending / mean_spending) if mean_spending > 0 else 0
                
                consistency = max(0, min(100, 100 - (variability * 100)))
                
                st.metric("Spending Consistency", f"{consistency:.1f}/100")
                
                if consistency > 80:
                    st.caption("Your spending is very consistent week-to-week")
                elif consistency > 50:
                    st.caption("Your spending has moderate variability between weeks")
                else:
                    st.caption("Your spending varies significantly from week to week")
            else:
                st.caption("Need more weekly data to calculate consistency")
        except Exception as e:
            st.caption(f"Couldn't calculate consistency. Error: {e}")
    else:
        st.caption("Add more transactions with dates to see consistency metrics")

with col2:
    if "Category" in data.columns and data["Category"].nunique() > 1:
        diversity = data["Category"].nunique()
        top_category = data.groupby("Category")["Amount"].sum().idxmax()
        top_category_percent = (data[data["Category"] == top_category]["Amount"].sum() / total_spent) * 100 if total_spent > 0 else 0
        
        st.metric("Top Category", f"{top_category}")
        st.caption(f"Represents {top_category_percent:.1f}% of your total spending")
    else:
        st.info("Add a 'Category' column to unlock category insights")

# Add tooltips to Transactions Over Time section
st.markdown("""
### 📅 Transactions Over Time 
<span class="tooltip">ℹ️
  <span class="tooltiptext">This chart shows your spending patterns over time. Each point represents the total spending for a week.</span>
</span>
""", unsafe_allow_html=True)

if "Date" in data.columns and not data.empty:
    # Ensure we have week data
    if 'Week' not in data.columns or 'Year' not in data.columns:
        data_copy = data.copy()
        data_copy.loc[:, 'Week'] = data_copy['Date'].dt.isocalendar().week
        data_copy.loc[:, 'Year'] = data_copy['Date'].dt.isocalendar().year
        data_copy.loc[:, 'YearWeek'] = data_copy['Year'].astype(str) + '-' + data_copy['Week'].astype(str)
        data = data_copy
    
    # Group by week instead of day
    weekly_totals = data.groupby(['Year', 'Week'])['Amount'].sum().reset_index()
    
    # Create a proper date field for the start of each week (for better plotting)
    weekly_totals['WeekStart'] = weekly_totals.apply(
        lambda x: datetime.strptime(f"{int(x['Year'])}-W{int(x['Week'])}-1", "%Y-W%W-%w"), 
        axis=1
    )
    
    if len(weekly_totals) > 1:
        # Create interactive plotly chart with tooltips
        fig = px.line(
            weekly_totals, 
            x="WeekStart", 
            y="Amount",
            markers=True,
            labels={"WeekStart": "Week Starting", "Amount": "Amount ($)"},
            title="Weekly Spending Over Time"
        )
        
        fig.update_layout(
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            ),
            xaxis_title="Week",
            yaxis_title="Amount ($)",
            plot_bgcolor="white",
            height=400
        )
        
        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=8),
            hovertemplate="<b>Week of:</b> %{x|%Y-%m-%d}<br><b>Amount:</b> $%{y:.2f}<extra></extra>"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional insights about the time series
        st.caption("""
        **Hover over points** to see exact amounts. Look for:
        - **Peaks**: Unusually high spending weeks
        - **Patterns**: Regular weekly spending cycles
        - **Trends**: Increasing or decreasing spending over time
        """)
    else:
        st.info("Not enough weekly transaction data to show a time trend.")
else:
    st.info("Add dates to your transactions to see spending over time.")

# Smart Income/Expense Analysis - works even without an explicit Type column
st.markdown("### 💸 Income vs Expenses")

# First, try to categorize income vs expense intelligently based on amount values
data_copy = data.copy()

# If Type column already exists with proper values, use it
has_valid_type = False
income_amount = 0
expense_amount = 0

if "Type" in data.columns and "TypeCategory" in data.columns and "Income" in data["TypeCategory"].values:
    has_valid_type = True
    type_data = data.groupby("TypeCategory")["Amount"].sum().reset_index()
    income_amount = type_data.loc[type_data["TypeCategory"] == "Income", "Amount"].sum()
    expense_amount = type_data.loc[type_data["TypeCategory"] == "Expense", "Amount"].sum()
else:
    # No explicit income/expense labeling, so infer from data patterns
    # Positive values might be expenses, negative or very large positive might be income
    # Apply heuristics to identify likely income vs expense
    try:
        # Sort by amount, descending
        sorted_df = data_copy.sort_values("Amount", ascending=False).copy()
        
        # Look at the distribution to identify potential income
        q75 = sorted_df["Amount"].quantile(0.75)
        q25 = sorted_df["Amount"].quantile(0.25)
        iqr = q75 - q25
        upper_threshold = q75 + (1.5 * iqr)  # Use IQR method to find outliers
        
        # Assume the largest outliers might be income
        potential_income = sorted_df[sorted_df["Amount"] > upper_threshold]
        
        # Also look for negative amounts which are often income
        negative_amounts = sorted_df[sorted_df["Amount"] < 0]
        
        # Create a TypeCategory column based on this analysis
        data_copy.loc[:, "TypeCategory"] = "Expense"  # Default all to expense
        
        # Mark potential income records
        if not potential_income.empty:
            for idx in potential_income.index:
                data_copy.loc[idx, "TypeCategory"] = "Income"
        
        # Mark negative amounts as income (with absolute value)
        if not negative_amounts.empty:
            for idx in negative_amounts.index:
                data_copy.loc[idx, "TypeCategory"] = "Income"
                # Take absolute value for visualization
                data_copy.loc[idx, "Amount"] = abs(data_copy.loc[idx, "Amount"])
        
        # Calculate totals
        type_data = data_copy.groupby("TypeCategory")["Amount"].sum().reset_index()
        
        # Only if we have both types
        if "Income" in type_data["TypeCategory"].values and "Expense" in type_data["TypeCategory"].values:
            income_amount = type_data.loc[type_data["TypeCategory"] == "Income", "Amount"].sum()
            expense_amount = type_data.loc[type_data["TypeCategory"] == "Expense", "Amount"].sum()
            has_valid_type = True
        else:
            # Try another approach - assume highest 10% of transactions might be income
            n_income = max(1, int(len(data_copy) * 0.1))
            top_rows = sorted_df.head(n_income).index
            
            data_copy.loc[:, "TypeCategory"] = "Expense"  # Reset
            data_copy.loc[top_rows, "TypeCategory"] = "Income"
            
            # Recalculate
            type_data = data_copy.groupby("TypeCategory")["Amount"].sum().reset_index()
            income_amount = type_data.loc[type_data["TypeCategory"] == "Income", "Amount"].sum()
            expense_amount = type_data.loc[type_data["TypeCategory"] == "Expense", "Amount"].sum()
            has_valid_type = True
    except Exception as e:
        st.caption(f"Error in income/expense analysis: {e}")
        has_valid_type = False

# Display the income/expense analysis
if has_valid_type:
    balance = income_amount - expense_amount
    
    # Show the bar chart - removed the duplicate financial metrics here
    if len(type_data) > 1:
        st.subheader("Income vs Expense Breakdown")
        fig = px.bar(
            type_data, 
            x="TypeCategory", 
            y="Amount",
            color="TypeCategory",
            color_discrete_map={"Income": "#2E8B57", "Expense": "#CD5C5C"},
            labels={"TypeCategory": "Type", "Amount": "Amount ($)"},
            text_auto=True
        )
        
        fig.update_traces(
            texttemplate='$%{y:,.2f}',
            textposition='inside',
            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>'
        )
        
        fig.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Amount ($)",
            plot_bgcolor="white",
            height=400,
            uniformtext=dict(mode="hide", minsize=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Analysis insights about the income/expense ratio
        if income_amount > 0 and expense_amount > 0:
            expense_to_income = expense_amount / income_amount * 100
            
            if expense_to_income < 70:
                st.success(f"✅ Great job! Your expenses are only {expense_to_income:.1f}% of your income.")
            elif expense_to_income < 90:
                st.info(f"ℹ️ Your expenses are {expense_to_income:.1f}% of your income - you're staying within your means.")
            elif expense_to_income < 100:
                st.warning(f"⚠️ Your expenses are {expense_to_income:.1f}% of your income - you're cutting it close!")
            else:
                st.error(f"❌ Your expenses are {expense_to_income:.1f}% of your income - you're spending more than you earn!")
else:
    st.info("Not enough transaction data to determine income and expenses. Try adding more varied transaction amounts.")

if "Category" in data.columns and data["Category"].nunique() > 1:
    st.markdown("### 📈 Spending by Category")
    
    category_data = data.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
    category_data = category_data[category_data["Amount"] > 0]
    
    if not category_data.empty:
        st.subheader("🥧 Category Distribution")
        
        if len(category_data) > 5:
            top_5 = category_data.head(5)
            others_sum = category_data.iloc[5:]["Amount"].sum()
            if others_sum > 0:
                top_5 = pd.concat([top_5, pd.DataFrame({"Category": ["Others"], "Amount": [others_sum]})])
            
            pie_data = top_5.copy()
            title = "Top 5 Categories Distribution"
        else:
            pie_data = category_data.copy()
            title = "Category Distribution"
        
        fig = px.pie(
            pie_data, 
            names='Category', 
            values='Amount',
            title=title,
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        
        fig.update_traces(
            textinfo='none',
            hoverinfo='label+percent+value',
            hovertemplate='<b>%{label}</b><br>Amount: $%{value:.2f}<br>Percentage: %{percent}<extra></extra>'
        )
        
        fig.update_layout(
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="right",
                x=1.1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("")
        
        st.subheader("📊 Category Breakdown (Bar Chart)")
        fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
        plot_data = category_data.head(10) if len(category_data) > 10 else category_data
        
        if not plot_data.empty:
            bars = sns.barplot(x="Amount", y="Category", data=plot_data, ax=ax_bar)
            ax_bar.set_xlabel("Amount ($)", fontsize=12)
            ax_bar.set_ylabel("Category", fontsize=12)
            ax_bar.tick_params(labelsize=10)
            
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

st.markdown("### 🧠 Smart Insights")

insights = []

if "Category" in data.columns and "Date" in data.columns and data["Category"].nunique() > 1:
    try:
        # Create a copy before modifying to avoid SettingWithCopyWarning
        insights_data = data.copy()
        insights_data.loc[:, "Month"] = insights_data["Date"].dt.to_period("M")
        
        category_frequency = insights_data.groupby("Category")["Month"].nunique()
        consistent_categories = category_frequency[category_frequency > 1].index.tolist()
        
        if consistent_categories:
            insights.append(f"🔄 You consistently spend on {', '.join(consistent_categories[:3])}{'...' if len(consistent_categories) > 3 else ''}")
    except Exception as e:
        st.caption(f"Error generating insights: {e}")

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

if "Date" in data.columns and "Amount" in data.columns and len(data) > 10:
    try:
        analysis_data = data.copy()
        analysis_data = analysis_data.sort_values("Date")
        half_point = len(analysis_data) // 2
        first_half = analysis_data.iloc[:half_point]
        second_half = analysis_data.iloc[half_point:]
        
        first_total = first_half["Amount"].sum()
        second_total = second_half["Amount"].sum()
        
        change_pct = ((second_total - first_total) / first_total) * 100 if first_total > 0 else 0
        
        if abs(change_pct) > 20:
            direction = "increased" if change_pct > 0 else "decreased"
            insights.append(f"📈 Your spending has {direction} by {abs(change_pct):.1f}% recently")
    except:
        pass

if insights:
    for insight in insights:
        st.markdown(f"- {insight}")
else:
    st.caption("Add more transaction data to unlock smart insights")

st.markdown("### 💡 Recommendations")

recommendations = []

recommendations.append("🔍 Categorize all transactions to get better insights")

if "Category" in data.columns and data["Category"].nunique() > 1:
    top_category = data.groupby("Category")["Amount"].sum().idxmax()
    recommendations.append(f"💰 Consider setting a budget for your highest spend category: {top_category}")

if "Date" in data.columns and len(data) > 10:
    recommendations.append("📆 Set up regular payment tracking to improve your financial visibility")

if recommendations:
    for i, recommendation in enumerate(recommendations[:3], 1):
        st.markdown(f"**{i}.** {recommendation}")
else:
    st.caption("Add more transaction data to unlock personalized recommendations")

st.markdown("---")
st.caption("💡 Tip: Upload more detailed transaction data to get even better insights and visualizations")