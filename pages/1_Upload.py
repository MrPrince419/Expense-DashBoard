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
import numpy as np
from datetime import datetime
import json
import io
import re

# Try to import PDF processing libraries
try:
    import pdfplumber
    import tabula
    PDF_PROCESSING_AVAILABLE = True
    logging.info("PDF processing libraries loaded successfully")
except ImportError as e:
    PDF_PROCESSING_AVAILABLE = False
    logging.error(f"PDF processing libraries import error: {e}")
    
    # Try to import them individually to provide better error messages
    try:
        import pdfplumber
        logging.info("pdfplumber loaded successfully")
    except ImportError as e:
        logging.error(f"pdfplumber import error: {e}")
    
    try:
        import tabula
        logging.info("tabula loaded successfully")
    except ImportError as e:
        logging.error(f"tabula import error: {e}")

# Improved profiling module imports with better fallback
PROFILING_AVAILABLE = None
try:
    from ydata_profiling import ProfileReport
    PROFILING_AVAILABLE = "ydata"
    st.success("✅ ydata-profiling loaded")
except ImportError:
    try:
        from pandas_profiling import ProfileReport
        PROFILING_AVAILABLE = "pandas"
        st.success("✅ pandas-profiling loaded")
    except ImportError:
        try:
            import sweetviz
            PROFILING_AVAILABLE = "sweetviz"
            st.success("✅ sweetviz loaded")
        except ImportError:
            PROFILING_AVAILABLE = None
            st.warning("For enhanced data profiling, install one of the following packages:", icon="⚠️")
            st.code("pip install ydata-profiling", language="bash")
            st.code("pip install pandas-profiling", language="bash")
            st.code("pip install sweetviz", language="bash")

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

# First, let's force load transactions at the top after checking auth
username = st.session_state["user"]
get_transactions()  # Force-load from disk into session_state if needed

# Initialize file upload flag if not present
if "file_uploaded" not in st.session_state:
    st.session_state["file_uploaded"] = False

# Add demo_active flag to persist demo mode across reruns
if "demo_active" not in st.session_state:
    st.session_state["demo_active"] = False

# Always try to load user data to ensure persistence across pages
if "transactions" not in st.session_state or st.session_state["transactions"].empty:
    user_data = load_user_data(username)
    if not user_data.empty:
        st.session_state["transactions"] = user_data.copy()
        
        # Also restore metadata if available
        metadata_file = os.path.join("user_data", f"{username}_metadata.json")
        try:
            if os.path.exists(metadata_file):
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    if "last_upload_filename" in metadata:
                        st.session_state["uploaded_file_name"] = metadata["last_upload_filename"]
                    if "last_upload_timestamp" in metadata:
                        st.session_state["upload_timestamp"] = metadata["last_upload_timestamp"]
                    if "upload_history" in metadata:
                        st.session_state["upload_history"] = metadata["upload_history"]
                st.success("Successfully loaded your saved data!")
        except Exception as e:
            logging.error(f"Error loading metadata: {e}")
else:
    # Log that we already have transactions in session state
    logging.info(f"Using existing session data with {len(st.session_state['transactions'])} transactions")

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

# Add Reset Upload button at the top level
reset_col1, reset_col2 = st.columns([4, 1])
with reset_col2:
    if st.button("🔁 Reset Upload", use_container_width=True):
        for key in ["file_uploaded", "demo_active", "transactions", "uploaded_file_name", "upload_timestamp"]:
            st.session_state.pop(key, None)
        st.rerun()

col1, col2 = st.columns([4, 1])

with col1:
    with st.container():
        uploaded_file = st.file_uploader(
            "Choose a file to upload",
            type=["csv", "xlsx", "xls", "json", "txt", "parquet", "zip", "pdf"],
            help="Supported formats: CSV, Excel, JSON, TXT, Parquet, ZIP, PDF",
            label_visibility="collapsed"
        )

with col2:
    demo_button = st.button("✨ View Demo", use_container_width=True, help="Load sample transaction data to try out the app")

with st.expander("ℹ️ Upload Instructions"):
    st.markdown("""
    Your file should contain at least:
    - **Name** (e.g., Store, Vendor, Description)
    - **Amount** (e.g., Price, Total, Cost)
    
    Optional columns like **Date** and **Category** will be inferred if missing or poorly named.
    Make sure the file is readable and not password-protected.
    """)

st.divider()

def load_sample_data():
    """Load the sample transaction data for demo purposes."""
    try:
        # Find the sample file
        sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Sample_Transactions.csv")
        if not os.path.exists(sample_path):
            # Try alternate location
            sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "sample_transactions.csv")
        
        if os.path.exists(sample_path):
            data = pd.read_csv(sample_path)
            
            # Ensure all required columns exist
            if "Type" not in data.columns:
                # Add Type column with "Expense" as default
                data["Type"] = "Expense"
                
                # Add some income transactions for better demo visualization
                # Set 10% of transactions as income
                income_count = max(3, int(len(data) * 0.1))
                income_indices = np.random.choice(data.index, income_count, replace=False)
                data.loc[income_indices, "Type"] = "Income"
            
            # Perform the same processing as with uploaded files
            data = filter_and_clean_data(data)
            
            # Make sure we have the correct count by forcing a copy
            processed_data = data.copy()
            
            # Explicitly set the session state variables
            st.session_state["transactions"] = processed_data
            st.session_state["uploaded_file_name"] = "Sample_Transactions.csv"
            st.session_state["upload_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if "upload_history" not in st.session_state:
                st.session_state["upload_history"] = []
            
            upload_metadata = {
                "filename": "Sample_Transactions.csv (Demo)",
                "timestamp": st.session_state["upload_timestamp"],
                "row_count": len(processed_data),
                "column_count": len(processed_data.columns)
            }
            
            # Add to history and limit to 10 entries
            st.session_state["upload_history"].insert(0, upload_metadata)
            st.session_state["upload_history"] = st.session_state["upload_history"][:10]
            
            # Save the demo data to the user's account
            if "user" in st.session_state:
                username = st.session_state["user"]
                metadata = {
                    "last_upload_filename": "Sample_Transactions.csv (Demo)",
                    "last_upload_timestamp": st.session_state["upload_timestamp"],
                    "upload_history": st.session_state["upload_history"]
                }
                save_user_data(username, processed_data, metadata)
                logging.info(f"Saved demo data to user account: {username}")
            
            # Just return the data - don't render UI elements here
            return processed_data
        else:
            st.error("Sample data file not found. Please contact the administrator.")
            logging.error(f"Sample file not found at {sample_path}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading sample data: {str(e)}")
        logging.error(f"Error loading sample data: {e}")
        return pd.DataFrame()

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

def extract_data_from_pdf(uploaded_file):
    """
    Extract transaction data from a PDF file.
    Uses intelligent pattern recognition for format-agnostic parsing.
    
    Args:
        uploaded_file: The uploaded PDF file
    
    Returns:
        DataFrame: Extracted transaction data
    """
    if not PDF_PROCESSING_AVAILABLE:
        st.error("PDF processing libraries are not available or couldn't be loaded")
        st.info("To enable PDF support, please run: `pip install pdfplumber tabula-py`")
        logging.error("PDF processing libraries not available")
        raise ValueError("PDF processing is not available. Please install required libraries (pdfplumber and tabula-py).")
    
    # Track any lines that failed parsing for user feedback
    error_log = []
    
    try:
        # Save the uploaded file to a temporary file
        pdf_data = uploaded_file.read()
        temp_file = io.BytesIO(pdf_data)
        
        # First try to use pdfplumber which doesn't require Java
        with st.spinner("Extracting and analyzing text from PDF..."):
            extracted_data = []
            
            try:
                with pdfplumber.open(temp_file) as pdf:
                    has_text = False
                    
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            has_text = True
                            lines = text.split('\n')
                            for line in lines:
                                # Skip headers and useless stuff
                                if len(line.strip()) < 8 or "balance" in line.lower():
                                    continue
                                
                                try:
                                    # Generic regex to find dates anywhere in the line
                                    date_match = re.search(r'(\d{1,2}[\s/-][A-Za-z]{3,9}[\s/-]\d{2,4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\b\w{3}\s\d{1,2}\b)', line)
                                    
                                    # Find all numbers that look like currency amounts
                                    amount_match = re.findall(r'[\d,]+\.\d{2}', line)
                                    
                                    if not amount_match:
                                        continue
                                    
                                    # Use the last number as the amount (common in statements)
                                    amount = float(amount_match[-1].replace(',', ''))
                                    
                                    # Use date if found, otherwise use today's date
                                    date = date_match.group(0) if date_match else pd.Timestamp.today().strftime('%Y-%m-%d')
                                    
                                    # Extract description by removing amounts
                                    description = re.sub(r'[\d,]+\.\d{2}', '', line)
                                    # Clean up extra whitespace
                                    description = re.sub(r'\s+', ' ', description).strip()
                                    
                                    # Auto-detect transaction type
                                    transaction_type = "Expense"
                                    if re.search(r'(received|deposit|credit|salary|income|refund|transfer\s+in)', description, re.IGNORECASE):
                                        transaction_type = "Income"
                                    
                                    extracted_data.append({
                                        'Date': date,
                                        'Name': description,
                                        'Amount': amount,
                                        'Type': transaction_type,
                                        'Category': 'Unknown'
                                    })
                                    
                                except Exception as e:
                                    error_log.append({"line": line, "error": str(e)})
                    
                    # Try OCR if no text was found in the PDF
                    if not has_text:
                        try:
                            # Check if pdf2image and pytesseract are available
                            import importlib.util
                            pdf2image_spec = importlib.util.find_spec("pdf2image")
                            pytesseract_spec = importlib.util.find_spec("pytesseract")
                            
                            if pdf2image_spec and pytesseract_spec:
                                import pytesseract
                                from pdf2image import convert_from_bytes
                                
                                st.info("PDF appears to be scanned. Using OCR to extract text...")
                                
                                # Reset the file pointer
                                temp_file.seek(0)
                                
                                # Convert PDF to images and extract text using OCR
                                images = convert_from_bytes(temp_file.getvalue())
                                text = ""
                                for img in images:
                                    text += pytesseract.image_to_string(img)
                                
                                # Process the OCR text line by line
                                for line in text.split('\n'):
                                    if len(line.strip()) < 8:
                                        continue
                                    
                                    try:
                                        # Same processing as above
                                        date_match = re.search(r'(\d{1,2}[\s/-][A-Za-z]{3,9}[\s/-]\d{2,4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\b\w{3}\s\d{1,2}\b)', line)
                                        amount_match = re.findall(r'[\d,]+\.\d{2}', line)
                                        
                                        if not amount_match:
                                            continue
                                        
                                        amount = float(amount_match[-1].replace(',', ''))
                                        date = date_match.group(0) if date_match else pd.Timestamp.today().strftime('%Y-%m-%d')
                                        description = re.sub(r'[\d,]+\.\d{2}', '', line)
                                        description = re.sub(r'\s+', ' ', description).strip()
                                        
                                        transaction_type = "Expense"
                                        if re.search(r'(received|deposit|credit|salary|income|refund|transfer\s+in)', description, re.IGNORECASE):
                                            transaction_type = "Income"
                                        
                                        extracted_data.append({
                                            'Date': date,
                                            'Name': description,
                                            'Amount': amount,
                                            'Type': transaction_type,
                                            'Category': 'Unknown'
                                        })
                                    except Exception as e:
                                        error_log.append({"line": line, "error": str(e)})
                            else:
                                st.warning("PDF appears to be scanned. Install pdf2image and pytesseract for OCR support.")
                                st.code("pip install pdf2image pytesseract", language="bash")
                        except ImportError:
                            st.warning("PDF appears to be scanned. Install pdf2image and pytesseract for OCR support.")
                            st.code("pip install pdf2image pytesseract", language="bash")
            except Exception as e:
                logging.error(f"pdfplumber extraction failed: {e}")
                st.error(f"Error extracting text: {str(e)}")
        
        # If pdfplumber found data, use it
        if extracted_data:
            # If there were any parsing errors, show them
            if error_log:
                with st.expander(f"⚠️ {len(error_log)} lines couldn't be fully parsed", expanded=False):
                    for i, error in enumerate(error_log[:10], 1):
                        st.markdown(f"**Line {i}:** `{error['line'][:50]}...`")
                        st.caption(f"Error: {error['error']}")
                    
                    if len(error_log) > 10:
                        st.caption(f"...and {len(error_log) - 10} more")
            
            st.success(f"✅ Successfully extracted {len(extracted_data)} transactions from PDF text")
            
            # Convert to dataframe
            result_df = pd.DataFrame(extracted_data)
            
            # Ensure all required columns exist with appropriate defaults
            for col in ["Date", "Name", "Amount", "Category", "Type"]:
                if col not in result_df.columns:
                    if col == "Amount":
                        result_df[col] = 0.0
                    elif col == "Date":
                        result_df[col] = pd.Timestamp.today().strftime('%Y-%m-%d')
                    elif col == "Type":
                        result_df[col] = "Expense"
                    else:
                        result_df[col] = "Unknown"
            
            # Enforce string type and fill NaN values for text columns to prevent validation errors
            result_df["Name"] = result_df["Name"].astype(str).fillna("Unknown")
            result_df["Category"] = result_df["Category"].astype(str).fillna("Uncategorized")
            result_df["Type"] = result_df["Type"].astype(str).fillna("Expense")
            
            return result_df
        
        # Otherwise try tabula (requires Java)
        try:
            with st.spinner("Analyzing PDF for tables..."):
                # Reset the file pointer
                temp_file.seek(0)
                
                tables = tabula.read_pdf(temp_file, pages='all', multiple_tables=True)
                
                # If tables were found, try to use them
                if tables and len(tables) > 0:
                    # Let user select which table to use if multiple were found
                    if len(tables) > 1:
                        selected_table_idx = st.selectbox(
                            "Multiple tables found in PDF. Select which one to use:", 
                            range(len(tables)),
                            format_func=lambda x: f"Table {x+1} ({len(tables[x])} rows)"
                        )
                        selected_table = tables[selected_table_idx]
                    else:
                        selected_table = tables[0]
                    
                    # If we have a good table, use it and return
                    if len(selected_table) > 0:
                        # Ensure all required columns exist
                        result_df = selected_table.copy()
                        for col in ["Date", "Name", "Amount", "Category", "Type"]:
                            if col not in result_df.columns:
                                if col == "Amount":
                                    # Try to find a numeric column that might be the amount
                                    numeric_cols = result_df.select_dtypes(include=['number']).columns
                                    if len(numeric_cols) > 0:
                                        result_df[col] = result_df[numeric_cols[0]]
                                    else:
                                        result_df[col] = 0.0
                                elif col == "Date":
                                    result_df[col] = pd.Timestamp.today().strftime('%Y-%m-%d')
                                elif col == "Type":
                                    result_df[col] = "Expense"
                                else:
                                    result_df[col] = "Unknown"
                        
                        st.success(f"✅ Successfully extracted table with {len(result_df)} transactions from PDF")
                        return result_df
        except Exception as e:
            logging.warning(f"Table extraction with tabula failed: {e}")
            st.warning("Could not extract structured tables from PDF. This may be due to missing Java dependency.")
            st.info("If you're seeing Java errors, make sure Java is installed on your system.")
        
        # If no automatic extraction worked, allow manual entry
        st.warning("Could not automatically extract transaction data from this PDF.")
        
        # Allow manual data specification as a fallback
        st.info("Please use the form below to manually enter transaction details:")
        
        # Simple manual input form
        with st.form("manual_transaction_form"):
            num_transactions = st.number_input("Number of transactions to add", 1, 50, 1)
            manual_data = []
            
            for i in range(int(num_transactions)):
                st.subheader(f"Transaction {i+1}")
                date = st.date_input(f"Date #{i+1}", value=pd.Timestamp.today())
                amount = st.number_input(f"Amount #{i+1}", value=0.0, step=0.01)
                name = st.text_input(f"Description/Merchant #{i+1}", value="")
                category = st.text_input(f"Category #{i+1}", value="Unknown")
                transaction_type = st.selectbox(f"Type #{i+1}", ["Expense", "Income"], index=0)
                
                manual_data.append({
                    'Date': date,
                    'Amount': amount,
                    'Name': name,
                    'Category': category,
                    'Type': transaction_type
                })
            
            submit = st.form_submit_button("Add Transactions")
            
            if submit:
                result_df = pd.DataFrame(manual_data)
                # Ensure all required columns exist
                for col in ["Date", "Name", "Amount", "Category", "Type"]:
                    if col not in result_df.columns:
                        if col == "Amount":
                            result_df[col] = 0.0
                        elif col == "Date":
                            result_df[col] = pd.Timestamp.today().strftime('%Y-%m-%d')
                        elif col == "Type":
                            result_df[col] = "Expense"
                        else:
                            result_df[col] = "Unknown"
                return result_df
        
        raise ValueError("Could not extract transaction data from PDF. Please try another file or format.")
            
    except Exception as e:
        logging.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Error processing PDF file: {e}")

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
        elif uploaded_file.name.endswith(".pdf"):
            # Call our PDF extraction function
            return extract_data_from_pdf(uploaded_file)
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

# Check if the demo button was clicked
if demo_button:
    # Set the demo_active flag to trigger the demo mode
    st.session_state["demo_active"] = True
    # If we don't have data already, load it now
    if "transactions" not in st.session_state or st.session_state["transactions"].empty:
        with st.spinner("Loading sample transaction data..."):
            data = load_sample_data()
    st.rerun()  # Updated to use st.rerun() instead of st.experimental_rerun()

# Use demo_active flag instead of demo_button to maintain state across reruns
if st.session_state["demo_active"]:
    # Make sure we have demo data loaded
    if "transactions" not in st.session_state or st.session_state["transactions"].empty:
        with st.spinner("Loading sample transaction data..."):
            data = load_sample_data()
    
    # Once data is loaded either way, show the interactive features
    if "transactions" in st.session_state and not st.session_state["transactions"].empty:
        st.success("✅ Demo data loaded successfully!")
        
        # Display all the data preview and analysis features
        with st.expander("📄 Preview Uploaded Data", expanded=True):
            st.info("🧼 Sample transaction data: pre-processed with standard columns")
            st.dataframe(st.session_state["transactions"].head(10))
        
        # Show duplicate detection option with the demo data
        if FUZZY_MATCHING_AVAILABLE and len(st.session_state["transactions"]) > 1:
            with st.expander("🔍 Duplicate Detection", expanded=True):
                st.info("Check for potential duplicate transactions in the demo data")
                duplicate_threshold = st.slider("Similarity threshold (%)", 50, 100, 80, key="demo_duplicate_threshold")
                
                if st.button("Check for Duplicates", key="demo_check_duplicates"):
                    with st.spinner("Analyzing transactions for duplicates..."):
                        duplicates = detect_duplicate_transactions(st.session_state["transactions"], duplicate_threshold)
                        
                        if not duplicates.empty:
                            st.warning(f"Found {len(duplicates)} potential duplicate transactions.")
                            st.dataframe(duplicates)
                            
                            csv = duplicates.to_csv(index=False)
                            st.download_button(
                                label="Download Duplicates Report",
                                data=csv,
                                file_name="potential_duplicates.csv",
                                mime="text/csv",
                                key="demo_duplicates_download"
                            )
                        else:
                            st.success("No potential duplicate transactions found!")
        
        # Show data profiling option with the demo data
        if PROFILING_AVAILABLE:
            with st.expander("📊 Advanced Data Profile", expanded=True):
                st.info("Generate a detailed profile of the demo transaction data")
                if st.button("Generate Detailed Data Profile", key="demo_generate_profile"):
                    with st.spinner("Generating comprehensive data profile..."):
                        profile_html = generate_data_profile(st.session_state["transactions"])
                        if profile_html:
                            st.components.v1.html(profile_html, height=600, scrolling=True)
                        else:
                            st.error("Failed to generate data profile. Check logs for details.")
        
        st.info("👀 You're viewing sample transaction data. Explore the dashboard to see analytics and charts!")

elif uploaded_file:
    # Add protection against reprocessing on every widget interaction
    if uploaded_file and not st.session_state["file_uploaded"]:
        try:
            data = process_uploaded_file(uploaded_file)
            st.session_state["transactions"] = data.copy()
            st.session_state["file_uploaded"] = True
            st.session_state["uploaded_file_name"] = uploaded_file.name
            st.session_state["upload_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update upload history
            if "upload_history" not in st.session_state:
                st.session_state["upload_history"] = []
                
            upload_metadata = {
                "filename": uploaded_file.name,
                "timestamp": st.session_state["upload_timestamp"],
                "row_count": len(data),
                "column_count": len(data.columns)
            }
            
            # Add to history and limit to 10 entries
            st.session_state["upload_history"].insert(0, upload_metadata)
            st.session_state["upload_history"] = st.session_state["upload_history"][:10]
            
            # Show success message
            st.success(f"✅ Successfully processed {uploaded_file.name} with {len(data)} transactions")
            
            # Save it immediately
            if "user" in st.session_state:
                metadata = {
                    "last_upload_filename": uploaded_file.name,
                    "last_upload_timestamp": st.session_state["upload_timestamp"],
                    "upload_history": st.session_state["upload_history"]
                }
                save_user_data(st.session_state["user"], data, metadata)
                
        except ValueError as e:
            st.error(str(e))
            st.session_state["file_uploaded"] = False
    
    # Show data profile expander regardless of whether we just processed the file or not
    if "transactions" in st.session_state and not st.session_state["transactions"].empty and PROFILING_AVAILABLE:
        with st.expander("📊 Advanced Data Profile", expanded=False):
            if st.button("Generate Detailed Data Profile"):
                with st.spinner("Generating comprehensive data profile..."):
                    profile_html = generate_data_profile(st.session_state["transactions"])
                    if profile_html:
                        st.components.v1.html(profile_html, height=600, scrolling=True)
                    else:
                        st.error("Failed to generate data profile. Check logs for details.")

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
    
    # Create a copy to avoid SettingWithCopyWarning
    if "transactions" in st.session_state:
        st.session_state["transactions"] = st.session_state["transactions"].copy()
        
        # Required columns for validation
        required_string_cols = ["Name", "Category", "Type"]
        
        # Add missing columns with defaults before conversion
        for col in required_string_cols:
            if col not in st.session_state["transactions"].columns:
                st.session_state["transactions"][col] = "Unknown"
        
        # Replace NaNs and enforce string type for all text columns
        st.session_state["transactions"][required_string_cols] = (
            st.session_state["transactions"][required_string_cols]
            .fillna("Unknown")
            .astype(str)
        )
        
        # Optional date check and standardization
        if "Date" in st.session_state["transactions"].columns:
            st.session_state["transactions"]["Date"] = pd.to_datetime(
                st.session_state["transactions"]["Date"], errors="coerce"
            ).fillna(pd.Timestamp.today())
        
        # Now safely save the data
        save_user_data(username, st.session_state["transactions"], metadata)
    else:
        st.warning("No transaction data available to save.")
    
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
    - **PDF**: Portable Document Format
    """)
with st.expander("How do I export my data?"):
    st.write("Select the desired format (CSV or Excel) and click the Export button. The data will be filtered and cleaned before export.")
with st.expander("What happens if my data has missing columns or messy names?"):
    st.write("The app will attempt to standardize column names and fill missing columns with empty values. It can work with just 'Date', 'Amount', and 'Name' fields. Ensure your data has at least these fields for basic functionality.")
with st.expander("Troubleshooting Upload Errors"):
    st.write("If you encounter issues while uploading your file:")
    st.markdown("- Ensure the file format is supported.\n- Check for corrupted or incomplete files.\n- Verify that the file is not password-protected.\n- Ensure the file size is within acceptable limits.")
with st.expander("How does PDF extraction work?"):
    st.markdown("""
    When you upload a PDF file, the app attempts to extract transaction data using multiple strategies:
    
    1. **Table Detection**: First, the app tries to identify and extract tables from the PDF (works best with bank statements and credit card bills)
    2. **Text Analysis**: If tables aren't found, the app analyzes the PDF text to find transaction patterns
    3. **Fallback Manual Entry**: If automated extraction fails, you can manually enter transaction details
    
    For best results with PDFs:
    - Use PDFs with clearly structured tables
    - Make sure the PDF is not encrypted or password-protected
    - PDF statements from major banks and credit card companies work best
    - OCR-processed PDFs (with text, not just images) provide better results
    """)