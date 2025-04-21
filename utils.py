"""
Utility module for data handling in the Expense Tracker application.
Manages loading, saving, validating, and processing user financial data.
"""
import os
import json
from json import JSONDecodeError  # Add this import for JSON error handling
import pandas as pd
from jsonschema import validate, ValidationError  # Removed unused imports like dotenv
from filelock import FileLock  # Add this import for file locking

from pathlib import Path  # Use pathlib for cross-platform file handling

DATA_DIR = Path("user_data")  # Updated to use pathlib

DATA_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Date": {"type": "string"},
            "Name": {"type": "string"},
            "Amount": {"type": "number"},
            "Category": {"type": "string"}
        },
        "required": ["Date", "Amount", "Name"]
    }
}

def get_user_file(username):
    """
    Get the file path for a user's transaction data.
    Creates the data directory if it doesn't exist.
    """
    DATA_DIR.mkdir(exist_ok=True)  # Create directory if it doesn't exist
    return DATA_DIR / f"{username}.json"

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
        # Identify new or changed rows
        existing_set = {tuple(row.items()) for row in existing_data}
        data_set = {tuple(row.items()) for row in data}
        new_or_changed = [dict(row) for row in (data_set - existing_set)]
    else:
        new_or_changed = data

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

def load_user_data(username):
    """
    Load a user's transaction data from their JSON file.
    Returns a DataFrame or an empty DataFrame if no data exists.
    """
    file_path = get_user_file(username)
    try:
        if file_path.exists():
            with file_path.open("r") as f:
                data = json.load(f)
                validate_user_data(data)
                return pd.DataFrame(data)
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Error loading user data: {e}")
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])  # Graceful handling for missing files
    except Exception as e:
        raise RuntimeError(f"Unexpected error while loading user data: {e}")

def save_user_data(username, df):
    """
    Save a user's transaction data to their JSON file.
    Handles datetime conversions, validates data, and prevents race conditions.
    """
    file_path = get_user_file(username)
    lock_path = f"{file_path}.lock"
    try:
        with FileLock(lock_path):
            df_copy = df.copy()
            for col in df_copy.select_dtypes(include=['datetime64']).columns:
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data = df_copy.to_dict(orient="records")
            existing_data = []
            if file_path.exists():
                with file_path.open("r") as f:
                    existing_data = json.load(f)
            validate_user_data(data, existing_data)
            with file_path.open("w") as f:
                json.dump(data, f, indent=4)
    except ValidationError as e:
        raise ValueError(f"Data validation error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while saving user data: {e}")