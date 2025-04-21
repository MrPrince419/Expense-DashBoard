"""
Utility module for data handling in the Expense Tracker application.
Manages loading, saving, validating, and processing user financial data.
"""
import os
import json
import datetime
from json import JSONDecodeError  # Add this import for JSON error handling
import pandas as pd
from jsonschema import validate, ValidationError  # Removed unused imports like dotenv
from filelock import FileLock  # Add this import for file locking
import streamlit as st  # Add this import for Streamlit session state

from pathlib import Path  # Use pathlib for cross-platform file handling

DATA_DIR = Path("user_data")  # Updated to use pathlib

# Fixed schema to expect objects instead of arrays
DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "Date": {"type": "string"},
        "Name": {"type": "string"},
        "Amount": {"type": "number"},
        "Category": {"type": "string"}
    },
    "required": ["Date", "Amount", "Name"]
}

def get_user_file(email):
    """
    Get the file path for a user's transaction data.
    Creates the data directory if it doesn't exist.
    
    Args:
        email (str): Email address of the user to identify the file
    """
    DATA_DIR.mkdir(exist_ok=True)  # Create directory if it doesn't exist
    sanitized_email = email.replace("@", "_at_").replace(".", "_dot_")  # Sanitize for filenames
    return DATA_DIR / f"{sanitized_email}.json"

def validate_rows(data, schema=DATA_SCHEMA):
    """
    Validate individual rows of data against the schema.
    Returns a list of invalid rows with error messages.
    """
    invalid_rows = []
    for index, row in enumerate(data):
        try:
            validate(instance=row, schema=schema)
        except ValidationError as e:
            invalid_rows.append((index, e.message))
    return invalid_rows

def validate_user_data(data, existing_data=None):
    """
    Validate user transaction data against the schema.
    Handles missing values and inconsistent formats.
    Validates only new or changed rows if existing_data is provided.
    Raises ValueError if any rows are invalid.
    """
    if existing_data is not None:
        # Use JSON serialization for reliable dictionary comparison
        existing_json = {json.dumps(row, sort_keys=True) for row in existing_data}
        new_json = {json.dumps(row, sort_keys=True) for row in data}
        new_or_changed = [json.loads(row) for row in (new_json - existing_json)]
    else:
        new_or_changed = data
    
    # Debug line to check the structure
    if new_or_changed and st.session_state.get('debug_mode'):
        print(f"Row sample: {new_or_changed[0]} -- type: {type(new_or_changed[0])}")

    # Fill missing values with defaults
    for row in new_or_changed:
        row.setdefault("Date", "Unknown")
        row.setdefault("Name", "Unknown")
        row.setdefault("Amount", 0.0)
        row.setdefault("Category", "Uncategorized")

    invalid_rows = validate_rows(new_or_changed)
    if invalid_rows:
        error_messages = "\n".join([f"Row {index}: {message}" for index, message in invalid_rows])
        raise ValueError(f"Invalid data format:\n{error_messages}")

def filter_and_clean_data(data):
    """
    Prepare data for export by cleaning and standardizing formats.
    Handles missing values, string trimming, and numeric conversions.
    """
    data = data.copy()

    # Fill missing values with defaults
    data["Date"] = data["Date"].fillna("Unknown")
    data["Name"] = data["Name"].fillna("Unknown")
    data["Amount"] = data["Amount"].fillna(0.0)
    data["Category"] = data["Category"].fillna("Uncategorized")

    # Clean string values by stripping whitespace
    for col in data.select_dtypes(include=["object"]).columns:
        if hasattr(data[col], "str") and hasattr(data[col].str, "strip"):
            data[col] = data[col].str.strip()

    # Convert numeric columns to proper numeric format
    for col in data.select_dtypes(include=["float", "int"]).columns:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)

    return data

def load_user_data(email):
    """
    Load a user's transaction data from their JSON file.
    
    Args:
        email (str): Email address of the user
    """
    file_path = get_user_file(email)
    try:
        if file_path.exists():
            with file_path.open("r") as f:
                data = json.load(f)
                validate_user_data(data)
                df = pd.DataFrame(data)
                
                # Convert date strings back to datetime objects
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                
                return df
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])
    except (json.JSONDecodeError, ValidationError) as e:
        st.error(f"Error loading user data: {e}")
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])  # Graceful handling for missing files
    except Exception as e:
        st.error(f"Unexpected error while loading user data: {e}")
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])

def save_user_data(email, df, metadata=None):
    """
    Save a user's transaction data to their JSON file.
    Handles datetime conversions, validates data, and prevents race conditions.
    
    Args:
        email (str): Email address of the user
        df (DataFrame): Transaction data
        metadata (dict, optional): Additional metadata
    """
    file_path = get_user_file(email)
    lock_path = f"{file_path}.lock"
    
    # Create metadata file path
    metadata_file = DATA_DIR / f"{email}_metadata.json"
    
    try:
        with FileLock(lock_path):
            # Create the data directory if it doesn't exist
            DATA_DIR.mkdir(exist_ok=True)
            
            df_copy = df.copy()
            # Convert datetime columns to strings
            for col in df_copy.select_dtypes(include=['datetime64']).columns:
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')

            # Handle native date types
            for col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, datetime.date) else x)

            data = df_copy.to_dict(orient="records")
            existing_data = []
            if file_path.exists():
                with file_path.open("r") as f:
                    existing_data = json.load(f)
            validate_user_data(data, existing_data)
            with file_path.open("w") as f:
                json.dump(data, f, indent=4)
                
            # Save metadata separately
            if metadata:
                with metadata_file.open("w") as f:
                    json.dump(metadata, f, indent=4)
    except ValidationError as e:
        raise ValueError(f"Data validation error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while saving user data: {e}")

def get_transactions():
    """
    Fetch transaction data reliably from session state or load it from the user's data file.
    Also loads metadata if available.
    
    Returns:
        DataFrame: The transaction data.
    """
    # Make sure we have the username
    if "user" not in st.session_state:
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])
    
    username = st.session_state["user"]
    
    # First check if we already have transactions in session state
    if "transactions" in st.session_state and not st.session_state["transactions"].empty:
        return st.session_state["transactions"]
    
    # If not in session state, try to load from the user's data file
    try:
        data = load_user_data(username)
        
        # If data was found, store it in session state for future access
        if not data.empty:
            st.session_state["transactions"] = data.copy()
            
            # Also load metadata
            metadata_file = DATA_DIR / f"{username}_metadata.json"
            if metadata_file.exists():
                with metadata_file.open("r") as f:
                    metadata = json.load(f)
                    # Store relevant metadata in session state
                    if "last_upload_filename" in metadata:
                        st.session_state["uploaded_file_name"] = metadata["last_upload_filename"]
                    if "last_upload_timestamp" in metadata:
                        st.session_state["upload_timestamp"] = metadata["last_upload_timestamp"]
                    if "upload_history" in metadata:
                        st.session_state["upload_history"] = metadata["upload_history"]
        
        return data
    except Exception as e:
        st.error(f"Error retrieving transactions: {e}")
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])