"""
Utility module for data handling in the Expense Tracker application.
Manages loading, saving, validating, and processing user financial data.
"""
import os
import json
import pandas as pd
import bcrypt
import jsonschema
from jsonschema import validate

# Directory for storing user transaction data
DATA_DIR = "user_data"

# Schema definition for validating transaction data
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
    
    Args:
        username (str): Username to get the file path for
        
    Returns:
        str: Absolute path to user's data file
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f"{username}.json")

def validate_user_data(data):
    """
    Validate user transaction data against the schema.
    
    Args:
        data (list): List of transaction dictionaries to validate
        
    Raises:
        ValueError: If the data doesn't match the required schema
    """
    try:
        validate(instance=data, schema=DATA_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Invalid data format: {e.message}")

def load_user_data(username):
    """
    Load a user's transaction data from their JSON file.
    
    Args:
        username (str): Username to load data for
        
    Returns:
        DataFrame: Pandas DataFrame containing user's transactions
        
    Raises:
        ValueError: If there's an error loading or parsing the data
    """
    file_path = get_user_file(username)
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                validate_user_data(data)
                return pd.DataFrame(data)
        # Return empty DataFrame with required columns if no data exists
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Error loading user data: {e}")

def save_user_data(username, df):
    """
    Save a user's transaction data to their JSON file.
    Handles datetime conversions and validates data before saving.
    
    Args:
        username (str): Username to save data for
        df (DataFrame): Pandas DataFrame containing transaction data
        
    Raises:
        ValueError: If there's an error validating or saving the data
    """
    file_path = get_user_file(username)
    try:
        # Create a copy to avoid modifying the original DataFrame
        df_copy = df.copy()
        
        # Convert datetime columns to string format for JSON serialization
        for col in df_copy.select_dtypes(include=['datetime64']).columns:
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle any Timestamp objects in object columns
        for col in df_copy.columns:
            if df_copy[col].dtype.name == 'object':
                if any(isinstance(x, pd.Timestamp) for x in df_copy[col].dropna()):
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x
                    )
        
        # Convert DataFrame to list of dictionaries for JSON serialization
        data = df_copy.to_dict(orient="records")
        
        # Validate the data before saving
        validate_user_data(data)
        
        # Write to file with pretty formatting (indent=4)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except ValueError as e:
        raise ValueError(f"Error saving user data: {e}")
    except Exception as e:
        raise ValueError(f"Error saving user data: {e}")

def hash_password(password):
    """
    Create a secure hash of a password using bcrypt.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    """
    Verify a password against its hash.
    
    Args:
        password (str): Plain text password to verify
        hashed (str): Stored hashed password to check against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_current_user():
    """
    Get the current user from the session state.
    
    Returns:
        str or None: Current username or None if not logged in
    """
    return st.session_state.get("username")