#!/usr/bin/env python3
"""
Reset script to clear all user data and restore default admin account.
This is useful for development and testing purposes.
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import hashlib
from passlib.hash import pbkdf2_sha256

def hash_answer(answer):
    """Create a hash of the secret answer (case-insensitive)."""
    return hashlib.sha256(answer.lower().encode()).hexdigest()

def main():
    print("🔄 Resetting application data...")
    
    # 1. Remove user_data directory and recreate it
    user_data_dir = Path("user_data")
    if user_data_dir.exists():
        shutil.rmtree(user_data_dir)
    user_data_dir.mkdir(exist_ok=True)
    print("✅ Cleared user data directory")
    
    # 2. Create default users.json with admin account
    admin_email = "admin@example.com"
    admin_password = "Admin@123456"
    
    users = {
        admin_email: {
            "email": admin_email,
            "password": pbkdf2_sha256.hash(admin_password),
            "secret_question": "Your favorite color?",
            "secret_answer": hash_answer("blue"),
            "role": "admin",
            "registration_date": datetime.now().isoformat(),
            "last_login": None,
            "activity_log": [],
            "login_count": 0,
            "upload_count": 0
        }
    }
    
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)
    print("✅ Created default users.json with admin account")
    
    # 3. Remove session.json if it exists
    session_file = Path("session.json")
    if session_file.exists():
        session_file.unlink()
        print("✅ Removed session.json")
    
    # 4. Remove admin_logs.txt if it exists
    admin_logs = Path("admin_logs.txt")
    if admin_logs.exists():
        admin_logs.unlink()
        print("✅ Removed admin_logs.txt")
    
    # 5. Remove any log files
    for log_file in Path(".").glob("*.log"):
        log_file.unlink()
        print(f"✅ Removed {log_file}")
    
    print("\n🎉 Data reset complete! The application now has a fresh environment.")
    print("\nDefault Admin Credentials:")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")

if __name__ == "__main__":
    # Confirm before proceeding
    print("⚠️  WARNING: This will delete all user data and reset the application! ⚠️")
    response = input("Do you want to continue? (y/N): ")
    
    if response.lower() == 'y':
        main()
    else:
        print("Operation cancelled.")
