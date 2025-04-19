import streamlit as st
from auth import restrict_access
from utils import load_user_data, save_user_data

restrict_access()

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("Please login to view this page.")
    st.stop()

if "user" not in st.session_state:
    st.error("Please login to view this page.")
    st.stop()

username = st.session_state["user"]
data = load_user_data(username)

import pandas as pd
import numpy as np

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("🏠 Home"):
        st.switch_page("app.py")
with col2:
    if st.button("📊 Dashboard"):
        st.switch_page("pages/2_Dashboard.py")
with col3:
    if st.button("🚪 Sign Out"):
        from auth import logout
        logout()
        st.switch_page("app.py")

st.divider()

try:
    import xlsxwriter
except ImportError:
    st.error("The required library 'xlsxwriter' is not installed. Please install it using 'pip install xlsxwriter'.")

st.title("Upload & Export")

st.subheader("Upload Your Financial Data")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls", "json", "txt", "parquet"])

def standardize_columns(data):
    column_mapping = {
        "amount spent": "Amount",
        "amt": "Amount",
        "transaction date": "Date",
        "name": "Name",
        "merchant": "Name",
        "description": "Name",
        "desc": "Name"
    }
    data.columns = [column_mapping.get(col.lower(), col) for col in data.columns]
    return data

def automatic_column_mapping(data):
    column_mapping = {
        "amount spent": "Amount",
        "amt": "Amount",
        "transaction date": "Date",
        "name": "Name",
        "merchant": "Name",
        "description": "Name",
        "desc": "Name"
    }

    mapped_columns = {}
    for col in data.columns:
        standardized_col = column_mapping.get(col.lower(), col)
        if standardized_col in mapped_columns.values():
            suffix = 1
            new_col = f"{standardized_col}_{suffix}"
            while new_col in mapped_columns.values():
                suffix += 1
                new_col = f"{standardized_col}_{suffix}"
            mapped_columns[col] = new_col
        else:
            mapped_columns[col] = standardized_col

    data.rename(columns=mapped_columns, inplace=True)
    return data

def load_uploaded_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx") or uploaded_file.name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith(".json"):
        return pd.read_json(uploaded_file)
    elif uploaded_file.name.endswith(".txt"):
        return pd.read_csv(uploaded_file, delimiter="\t")
    elif uploaded_file.name.endswith(".parquet"):
        return pd.read_parquet(uploaded_file)
    else:
        raise ValueError("Unsupported file format. Please upload CSV, Excel, JSON, TXT, or Parquet files.")

if uploaded_file:
    with st.spinner("Processing your file..."):
        try:
            data = load_uploaded_file(uploaded_file)

            data = automatic_column_mapping(data)

            required_columns = ["Date", "Amount", "Name"]
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")

            invalid_rows = data[data[required_columns].isnull().any(axis=1)]
            if not invalid_rows.empty:
                st.warning("Some rows have missing values in required columns. These rows are highlighted below:")
                st.dataframe(invalid_rows)

            st.session_state["transactions"] = data
            
            from auth import log_user_activity
            log_user_activity(username, "upload")
            
            st.write("### Preview of Uploaded Data")
            st.dataframe(data)
        except Exception as e:
            st.error(f"Error loading file: {e}")

if "transactions" in st.session_state:
    st.write("### Data Summary")
    num_rows = len(st.session_state["transactions"])
    num_columns = len(st.session_state["transactions"].columns)
    num_missing = st.session_state["transactions"].isnull().sum().sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", num_rows)
    col2.metric("Columns", num_columns)
    col3.metric("Missing Values", num_missing)

    st.write("### Data Cleaning Options")
    remove_duplicates = st.checkbox("Remove Duplicates")
    fill_missing = st.checkbox("Fill Missing Values with 'Unknown'")

    if remove_duplicates or fill_missing:
        cleaned_data = st.session_state["transactions"].copy()

        if remove_duplicates:
            original_count = len(cleaned_data)
            cleaned_data = cleaned_data.drop_duplicates()
            removed_count = original_count - len(cleaned_data)
            if removed_count > 0:
                st.success(f"Removed {removed_count} duplicate rows")

        if fill_missing:
            missing_count = cleaned_data.isnull().sum().sum()
            if missing_count > 0:
                cleaned_data = cleaned_data.fillna("Unknown")
                st.success(f"Filled {missing_count} missing values with 'Unknown'")
            else:
                st.info("No missing values found")

        st.session_state["transactions"] = cleaned_data.copy()

        save_user_data(username, st.session_state["transactions"])

def filter_and_clean_data(data):
    data = data.copy()
    data = data.dropna()
    for col in data.select_dtypes(include=['object']).columns:
        if hasattr(data[col], 'str') and hasattr(data[col].str, 'strip'):
            data[col] = data[col].str.strip()
    for col in data.select_dtypes(include=['float', 'int']).columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    return data

if "transactions" in st.session_state:
    st.subheader("Export Data")
    filtered_data = filter_and_clean_data(st.session_state["transactions"])
    export_format = st.selectbox("Select export format", ["CSV", "Excel"])
    if export_format == "CSV":
        st.download_button(
            label="Download Filtered Data as CSV",
            data=filtered_data.to_csv(index=False),
            file_name="filtered_data.csv",
            mime="text/csv"
        )
    elif export_format == "Excel":
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            filtered_data.to_excel(writer, index=False, sheet_name="Filtered Data")
        st.download_button(
            label="Download Filtered Data as Excel",
            data=output.getvalue(),
            file_name="filtered_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.subheader("FAQ")
with st.expander("What file formats are supported?"):
    st.write("You can upload the following file formats:")
    st.markdown("- **CSV**: Comma-separated values\n- **Excel**: .xlsx, .xls\n- **JSON**: JavaScript Object Notation\n- **TXT**: Tab-delimited text files\n- **Parquet**: Columnar storage format")
with st.expander("How do I export my data?"):
    st.write("Select the desired format (CSV or Excel) and click the Export button. The data will be filtered and cleaned before export.")
with st.expander("What happens if my data has missing columns or messy names?"):
    st.write("The app will attempt to standardize column names and fill missing columns with empty values. It can work with just 'Date', 'Amount', and 'Name' fields. Ensure your data has at least these fields for basic functionality.")
with st.expander("Troubleshooting Upload Errors"):
    st.write("If you encounter issues while uploading your file:")
    st.markdown("- Ensure the file format is supported.\n- Check for corrupted or incomplete files.\n- Verify that the file is not password-protected.\n- Ensure the file size is within acceptable limits.")