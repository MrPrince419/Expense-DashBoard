#!/usr/bin/env python3
"""
Pre-commit check to ensure no sensitive data is being committed.
Run this script before committing to verify your repository is clean.
"""
import os
import re
import glob
import sys
from pathlib import Path

def print_header(text):
    print(f"\n{'=' * 80}")
    print(f" {text}")
    print(f"{'=' * 80}")

def check_sensitive_patterns(file_path, patterns):
    """Check if file contains sensitive patterns."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            content = f.read()
            for pattern_name, pattern in patterns.items():
                if re.search(pattern, content):
                    print(f"❌ {file_path}: Contains {pattern_name}")
                    return False
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return True

def is_excluded(file_path, excluded_patterns):
    """Check if file should be excluded from checks."""
    for pattern in excluded_patterns:
        if re.search(pattern, str(file_path)):
            return True
    return False

def main():
    print_header("PRE-COMMIT SECURITY CHECK")
    
    # Files and directories to exclude from checks
    excluded_patterns = [
        r'\.git/',
        r'\.gitignore$',
        r'\.pyc$',
        r'__pycache__/',
        r'venv/',
        r'env/',
        r'\.pytest_cache/',
        r'\.vscode/',
        r'\.idea/',
        r'\.DS_Store$',
        r'Thumbs\.db$',
        r'pre_commit_check\.py$',
        r'\.env\.example$',
    ]
    
    # Patterns to check for
    sensitive_patterns = {
        'email address': r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+(?!example\.com)',
        'IP address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'password': r'password\s*=\s*["\'](?!Admin@123456|Admin@123)[^"\']+["\']',
        'api key': r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
        'secret key': r'secret[_-]?key\s*=\s*["\'][^"\']+["\']',
        'access token': r'(?:access|auth|jwt|oauth)[_-]?token\s*=\s*["\'][^"\']+["\']',
        'database credentials': r'(?:db|database|mongo|postgresql)_(?:uri|url|connection)\s*=\s*["\'][^"\']+["\']',
    }
    
    # Directories to check (excluding those in .gitignore)
    base_dir = Path(".")
    
    # Files to check
    file_types = ['*.py', '*.json', '*.md', '*.txt', '*.html', '*.js', '*.css']
    files_to_check = []
    
    for file_type in file_types:
        for file_path in base_dir.glob(f"**/{file_type}"):
            file_path_str = str(file_path)
            if not is_excluded(file_path_str, excluded_patterns):
                files_to_check.append(file_path)
    
    # Check files
    all_clean = True
    for file_path in files_to_check:
        if not check_sensitive_patterns(file_path, sensitive_patterns):
            all_clean = False
    
    # Check for user data files that shouldn't be committed
    user_data_files = list(base_dir.glob("user_data/*.json"))
    if user_data_files:
        print(f"❌ Found {len(user_data_files)} user data files that should not be committed.")
        for file in user_data_files[:5]:  # Show first 5 as examples
            print(f"   - {file}")
        if len(user_data_files) > 5:
            print(f"   - ... and {len(user_data_files) - 5} more")
        all_clean = False
    
    # Check for session and user files
    sensitive_files = [
        "users.json", 
        "session.json", 
        "admin_logs.txt", 
        ".env",
        "auth_debug.log",
        "upload.log"
    ]
    
    for file in sensitive_files:
        if os.path.exists(file):
            print(f"❌ Sensitive file {file} exists and is not excluded by .gitignore")
            all_clean = False
    
    if all_clean:
        print("\n✅ All checks passed! No sensitive information detected.")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above before committing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
