"""
Upload & Export page for the Expense Tracker application.
Handles data importing from various file formats, column mapping,
data cleaning, and exporting processed data.
"""
import streamlit as st

# Set the page layout to wide mode - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="Upload & Export", layout="wide")

from auth import restrict_access
from utils import load_user_data, save_user_data, filter_and_clean_data, get_transactions
import pandas as pd
import logging
import os
from datetime import datetime

try:
    from ydata_profiling import ProfileReport
    PROFILING_AVAILABLE = "ydata"
    st.info("✅ ydata-profiling loaded")
except Exception as e:
    st.error(f"❌ Failed to import ydata-profiling: {e}")
    try:
        from pandas_profiling import ProfileReport
        PROFILING_AVAILABLE = "pandas"
        st.info("✅ pandas-profiling loaded")
    except Exception as e:
        st.error(f"❌ Failed to import pandas-profiling: {e}")
        try:
            import sweetviz
            PROFILING_AVAILABLE = "sweetviz"
            st.info("✅ sweetviz loaded")
        except Exception as e:
            PROFILING_AVAILABLE = None
            st.warning("Install 'ydata-profiling' for enhanced data profiling: `pip install ydata-profiling`", icon="⚠️")
            st.error(f"❌ All profiling imports failed: {e}")

try:
    from rapidfuzz import process, fuzz
    FUZZY_MATCHING_AVAILABLE = True
except ImportError:
    FUZZY_MATCHING_AVAILABLE = False
    st.warning("Install 'rapidfuzz' for better column matching: `pip install rapidfuzz`", icon="⚠️")

logging.basicConfig(
    filename="upload.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

st.markdown("""
<style>
[data-testid="stFileUploader"] section {
    padding: 0;
}
[data-testid="stFileUploader"] section > input + div {
    display: none;
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

username = st.session_state["user"]
data = get_transactions()

if "transactions" not in st.session_state or st.session_state["transactions"].empty:
    user_data = load_user_data(username)
    if not user_data.empty:
        st.session_state["transactions"] = user_data.copy()
        st.success("Successfully loaded your saved data!")

st.markdown(
    f"<div><strong>👤 {st.session_state['user']}</strong></div><hr>",
    unsafe_allow_html=True
)

st.title("Upload & Export")

if "uploaded_file_name" in st.session_state and "upload_timestamp" in st.session_state:
    st.caption(f"Last uploaded: `{st.session_state['uploaded_file_name']}` on {st.session_state['upload_timestamp']}")
elif "transactions" in st.session_state and not st.session_state["transactions"].empty:
    st.caption(f"You have {len(st.session_state['transactions'])} transactions loaded")

st.markdown("### 📁 Upload a Transaction File")

with st.container():
    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        type=["csv", "xlsx", "xls", "json", "txt", "parquet", "zip"],
        help="Supported formats: CSV, Excel, JSON, TXT, Parquet, ZIP",
        label_visibility="collapsed"
    )

    with st.expander("ℹ️ Upload Instructions"):
        st.markdown("""
        Your file should contain at least:
        - **Name** (e.g., Store, Vendor, Description)
        - **Amount** (e.g., Price, Total, Cost)
        
        Optional columns like **Date** and **Category** will be inferred if missing or poorly named.
        Make sure the file is readable and not password-protected.
        """)

st.divider()

def fuzzy_column_match(col_name, possible_targets, threshold=70):
    """Use fuzzy matching to find the best match for a column name."""
    if not FUZZY_MATCHING_AVAILABLE:
        for target in possible_targets:
            if target in col_name.lower():
                return target
        return None
    
    match, score, _ = process.extractOne(col_name.lower(), possible_targets)
    return match if score >= threshold else None

def detect_duplicate_transactions(data, threshold=80):
    """
    Detect potential duplicate transactions using fuzzy matching.
    
    Args:
        data (DataFrame): Transaction data
        threshold (int): Fuzzy matching threshold (0-100)
        
    Returns:
        DataFrame: Potential duplicate transactions with similarity scores
    """
    if not FUZZY_MATCHING_AVAILABLE or len(data) < 2:
        return pd.DataFrame()
    
    data['amount_str'] = data['Amount'].astype(str)
    
    potential_duplicates = []
    
    max_rows_to_check = 1000
    if len(data) > max_rows_to_check:
        st.warning(f"Limiting duplicate detection to first {max_rows_to_check} transactions for performance reasons.")
        check_data = data.head(max_rows_to_check)
    else:
        check_data = data
    
    for i, row1 in check_data.iterrows():
        fingerprint1 = f"{row1['Name']} {row1['amount_str']}"
        
        for j, row2 in check_data.iterrows():
            if i >= j:
                continue
                
            fingerprint2 = f"{row2['Name']} {row2['amount_str']}"
            
            similarity = fuzz.ratio(fingerprint1.lower(), fingerprint2.lower())
            
            if similarity >= threshold:
                potential_duplicates.append({
                    'Index1': i,
                    'Index2': j,
                    'Transaction1': fingerprint1,
                    'Transaction2': fingerprint2,
                    'Similarity': similarity,
                    'Date1': row1.get('Date', 'Unknown'),
                    'Date2': row2.get('Date', 'Unknown')
                })
    
    if potential_duplicates:
        dup_df = pd.DataFrame(potential_duplicates)
        return dup_df.sort_values('Similarity', ascending=False)
    
    return pd.DataFrame()

def generate_data_profile(data):
    """Generate an interactive data profile report using available profiling library."""
    if not PROFILING_AVAILABLE:
        return None
    
    try:
        if PROFILING_AVAILABLE == "ydata" or PROFILING_AVAILABLE == "pandas":
            profile = ProfileReport(data, title="Transaction Data Profile", minimal=True)
            return profile.to_html()
        elif PROFILING_AVAILABLE == "sweetviz":
            report = sweetviz.analyze(data)
            report_path = "transaction_report.html"
            report.show_html(report_path)
            with open(report_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        logging.error(f"Failed to generate data profile: {e}")
        return None

def process_uploaded_file(uploaded_file):
    """
    Process the uploaded file and return a cleaned DataFrame with intelligently mapped columns.
    """
    try:
        if uploaded_file.name.endswith(".zip"):
            import zipfile
            import io
            
            with zipfile.ZipFile(uploaded_file) as z:
                supported_formats = [".csv", ".xlsx", ".xls", ".json", ".txt", ".parquet"]
                for filename in z.namelist():
                    if any(filename.endswith(fmt) for fmt in supported_formats):
                        with z.open(filename) as file:
                            file_content = io.BytesIO(file.read())
                            file_content.name = filename
                            return process_uploaded_file(file_content)
                            
            raise ValueError("No supported files found in ZIP archive.")
                
        if uploaded_file.name.endswith(".csv"):
            data = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith((".xlsx", ".xls")):
            excel_file = pd.ExcelFile(uploaded_file)
            if len(excel_file.sheet_names) > 1:
                sheet_name = st.selectbox("Select sheet:", excel_file.sheet_names)
                data = pd.read_excel(excel_file, sheet_name=sheet_name)
            else:
                data = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".json"):
            data = pd.read_json(uploaded_file)
        elif uploaded_file.name.endswith(".txt"):
            data = pd.read_csv(uploaded_file, delimiter="\t")
        elif uploaded_file.name.endswith(".parquet"):
            data = pd.read_parquet(uploaded_file)
        else:
            raise ValueError("Unsupported file format.")

        uploaded_file.seek(0, os.SEEK_END)
        file_size_mb = uploaded_file.tell() / (1024 * 1024)
        uploaded_file.seek(0)
        
        row_count = len(data)
        
        if file_size_mb > 50:
            st.warning(f"Large file detected ({file_size_mb:.1f} MB). Processing may take longer.", icon="⚠️")
        if row_count > 50000:
            st.warning(f"Large dataset detected ({row_count:,} rows). Consider using a smaller sample for better performance.", icon="⚠️")

        if data.empty or len(data.columns) == 0:
            raise ValueError("The uploaded file appears to be empty or has no recognizable columns.")

        if all(str(col).lower().startswith("unnamed") or str(col).isdigit() for col in data.columns):
            data.columns = [f"col_{i}" for i in range(data.shape[1])]
            logging.info("Detected headerless file and renamed columns.")

        data.columns = [str(col).strip().lower() for col in data.columns]

        if all(str(c).isdigit() for c in data.columns[:3]):
            data.columns = [f"Column_{i}" for i in range(len(data.columns))]

        desired_columns = {
            "Amount": ["amount", "sum", "price", "cost", "total", "payment", "value", "expense"],
            "Name": ["name", "merchant", "vendor", "store", "description", "desc", "transaction", "details", "item"],
            "Date": ["date", "time", "day", "when", "timestamp"],
            "Category": ["category", "cat", "type", "group", "label", "classification"]
        }

        col_map = {}
        for col in data.columns:
            matched = False
            for std_col, aliases in desired_columns.items():
                if FUZZY_MATCHING_AVAILABLE:
                    match = fuzzy_column_match(col, aliases)
                    if match:
                        col_map[col] = std_col
                        matched = True
                        break
                else:
                    if any(alias in col.lower() for alias in aliases):
                        col_map[col] = std_col
                        matched = True
                        break
            
            if not matched:
                col_map[col] = col

        data.rename(columns=col_map, inplace=True)

        data = data.loc[:, ~data.columns.duplicated()]

        required_cols = ["Name", "Amount", "Date", "Category"]
        for col in required_cols:
            if col not in data.columns:
                if col == "Amount":
                    data[col] = 0.0
                    logging.info(f"Created missing {col} column with default value 0.0")
                elif col == "Date":
                    data[col] = pd.to_datetime("today").date()
                    logging.info(f"Created missing {col} column with today's date")
                else:
                    data[col] = "Unknown"
                    logging.info(f"Created missing {col} column with default value 'Unknown'")

        if "Name" in data.columns and "Amount" in data.columns and "Date" not in data.columns:
            data["Date"] = pd.Timestamp.today().strftime("%Y-%m-%d")
            logging.info("Added placeholder Date column to dataset with only Name and Amount")
        
        if "Amount" not in data.columns:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                data.rename(columns={numeric_cols[0]: "Amount"}, inplace=True)
                logging.info(f"Auto-detected Amount column from numeric column: {numeric_cols[0]}")
        
        data.fillna("Unknown", inplace=True)

        data = filter_and_clean_data(data)

        if "Category" in data.columns:
            data["Category"] = data["Category"].astype(str).str.strip().str.title()

        if "Name" in data.columns:
            data["Name"] = data["Name"].astype(str).str.strip()

        if "Date" in data.columns:
            try:
                data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
                data = data.sort_values(by="Date", ascending=False)
            except Exception as e:
                logging.warning(f"Could not sort by Date: {e}")

        if all(col in data.columns for col in ["Category", "Date"]):
            data = data.sort_values(by=["Category", "Date"], ascending=[True, False])

        logging.info(f"Processed upload: {uploaded_file.name}")
        return data

    except Exception as e:
        logging.error(f"File processing failed: {e}")
        raise ValueError(f"Error processing file: {e}")

if uploaded_file:
    try:
        data = process_uploaded_file(uploaded_file)
        st.session_state["transactions"] = data.copy()
        st.session_state["uploaded_file_name"] = uploaded_file.name
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["upload_timestamp"] = current_time
        
        if "upload_history" not in st.session_state:
            st.session_state["upload_history"] = []
        
        upload_metadata = {
            "filename": uploaded_file.name,
            "timestamp": current_time,
            "row_count": len(data),
            "column_count": len(data.columns)
        }
        
        st.session_state["upload_history"].insert(0, upload_metadata)
        st.session_state["upload_history"] = st.session_state["upload_history"][:10]
        
        st.success("✅ File uploaded successfully!")

        with st.expander("📄 Preview Uploaded Data", expanded=True):
            st.info("🧼 Cleaned & organized: fuzzy-matched columns, sorted by category/date, trimmed text, filled missing values.")
            st.dataframe(data.head())
        
        if FUZZY_MATCHING_AVAILABLE and len(data) > 1:
            with st.expander("🔍 Duplicate Detection", expanded=False):
                duplicate_threshold = st.slider("Similarity threshold (%)", 50, 100, 80)
                
                if st.button("Check for Duplicates"):
                    with st.spinner("Analyzing transactions for duplicates..."):
                        duplicates = detect_duplicate_transactions(data, duplicate_threshold)
                        
                        if not duplicates.empty:
                            st.warning(f"Found {len(duplicates)} potential duplicate transactions.")
                            st.dataframe(duplicates)
                            
                            csv = duplicates.to_csv(index=False)
                            st.download_button(
                                label="Download Duplicates Report",
                                data=csv,
                                file_name="potential_duplicates.csv",
                                mime="text/csv"
                            )
                        else:
                            st.success("No potential duplicate transactions found!")
        
        if PROFILING_AVAILABLE:
            with st.expander("📊 Advanced Data Profile", expanded=False):
                if st.button("Generate Detailed Data Profile"):
                    with st.spinner("Generating comprehensive data profile..."):
                        profile_html = generate_data_profile(data)
                        if profile_html:
                            st.components.v1.html(profile_html, height=600, scrolling=True)
                        else:
                            st.error("Failed to generate data profile. Check logs for details.")

    except ValueError as e:
        st.error(str(e))

if "transactions" in st.session_state and not st.session_state["transactions"].empty:
    with st.expander("📊 Data Summary", expanded=False):
        num_rows = len(st.session_state["transactions"])
        num_columns = len(st.session_state["transactions"].columns)
        num_missing = st.session_state["transactions"].isnull().sum().sum()
        st.markdown(f"**Total Rows:** `{num_rows}` | **Columns:** `{num_columns}` | **Missing Values:** `{num_missing}`")
    
    if "upload_history" in st.session_state and st.session_state["upload_history"]:
        with st.expander("📂 Upload History", expanded=False):
            for i, upload in enumerate(st.session_state["upload_history"], 1):
                st.markdown(f"**{i}.** `{upload['filename']}` - {upload['timestamp']} ({upload['row_count']} rows, {upload['column_count']} columns)")
    
    metadata = {
        "last_upload_filename": st.session_state.get("uploaded_file_name", "Unknown"),
        "last_upload_timestamp": st.session_state.get("upload_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "upload_history": st.session_state.get("upload_history", [])
    }
    
    save_user_data(username, st.session_state["transactions"], metadata)
    
    st.info("💾 Your data is automatically saved and will be available when you return to this page.")
else:
    with st.expander("📊 Data Summary", expanded=False):
        st.markdown("**Total Rows:** `0` | **Columns:** `0` | **Missing Values:** `0`")

if "transactions" in st.session_state:
    st.subheader("⬇️ Export Your Cleaned Data")
    filtered_data = filter_and_clean_data(st.session_state["transactions"])
    export_format = st.selectbox("Choose export format:", ["CSV", "Excel"])
    
    if export_format == "CSV":
        st.download_button(
            label="Download CSV",
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
            label="Download Excel File",
            data=output.getvalue(),
            file_name="filtered_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.subheader("FAQ")
with st.expander("What file formats are supported?"):
    st.write("You can upload the following file formats:")
    st.markdown("""
    - **CSV**: Comma-separated values
    - **Excel**: .xlsx, .xls (including multi-sheet files)
    - **JSON**: JavaScript Object Notation
    - **TXT**: Tab-delimited text files
    - **Parquet**: Columnar storage format
    - **ZIP**: Contains any of the above formats
    """)
with st.expander("How do I export my data?"):
    st.write("Select the desired format (CSV or Excel) and click the Export button. The data will be filtered and cleaned before export.")
with st.expander("What happens if my data has missing columns or messy names?"):
    st.write("The app will attempt to standardize column names and fill missing columns with empty values. It can work with just 'Date', 'Amount', and 'Name' fields. Ensure your data has at least these fields for basic functionality.")
with st.expander("Troubleshooting Upload Errors"):
    st.write("If you encounter issues while uploading your file:")
    st.markdown("- Ensure the file format is supported.\n- Check for corrupted or incomplete files.\n- Verify that the file is not password-protected.\n- Ensure the file size is within acceptable limits.")