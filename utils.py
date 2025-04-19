import os
import json
import pandas as pd
import bcrypt
import jsonschema
from jsonschema import validate

DATA_DIR = "user_data"

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
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f"{username}.json")

def validate_user_data(data):
    try:
        validate(instance=data, schema=DATA_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Invalid data format: {e.message}")

def load_user_data(username):
    file_path = get_user_file(username)
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                validate_user_data(data)
                return pd.DataFrame(data)
        return pd.DataFrame(columns=["Date", "Name", "Amount", "Category"])
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Error loading user data: {e}")

def save_user_data(username, df):
    file_path = get_user_file(username)
    try:
        df_copy = df.copy()
        
        for col in df_copy.select_dtypes(include=['datetime64']).columns:
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        for col in df_copy.columns:
            if df_copy[col].dtype.name == 'object':
                if any(isinstance(x, pd.Timestamp) for x in df_copy[col].dropna()):
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x
                    )
        
        data = df_copy.to_dict(orient="records")
        validate_user_data(data)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except ValueError as e:
        raise ValueError(f"Error saving user data: {e}")
    except Exception as e:
        raise ValueError(f"Error saving user data: {e}")

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_current_user():
    return st.session_state.get("username")