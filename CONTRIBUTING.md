# Contributing to Expense Tracker

Thank you for your interest in contributing to the Expense Tracker project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Workflow](#workflow)
- [Security Considerations](#security-considerations)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up your development environment
4. Create a feature branch
5. Make your changes
6. Test your changes
7. Submit a pull request

## Development Environment

### Setting Up

1. Create a virtual environment:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment variables template:
   ```bash
   cp .env.example .env
   ```

4. Reset the application data to start fresh:
   ```bash
   python reset_data.py
   ```

5. Run the application:
   ```bash
   streamlit run app.py
   ```

## Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the style guidelines

3. Run the pre-commit checks:
   ```bash
   python pre_commit_check.py
   ```

4. Run tests:
   ```bash
   pytest
   ```

5. Commit your changes with a descriptive message:
   ```bash
   git commit -m "Feature: Add description of your changes"
   ```

6. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

7. Create a pull request on GitHub

## Security Considerations

### Handling Sensitive Data

- NEVER commit real user data, passwords, API keys, or other sensitive information
- Use the provided `.env.example` file as a template and `.env` for actual values (which is git-ignored)
- Always run `python pre_commit_check.py` before committing to catch any unintended sensitive data

### Testing with Sample Data

- Use the provided sample data in the `sample_data` directory for testing
- For more complex test scenarios, create your own test data but ensure it doesn't contain sensitive information

### Reporting Security Issues

If you discover a security vulnerability, please do NOT open an issue. Email us directly at [security@example.com](mailto:security@example.com).

## Testing

- Write tests for all new features
- Tests should be placed in the `tests` directory
- Run tests with `pytest`
- Ensure that all tests pass before submitting a pull request

## Submitting Changes

- Ensure all tests pass
- Ensure the pre-commit check passes
- Update documentation if needed
- Create a pull request with a clear description of the changes

## Style Guidelines

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Write docstrings for all functions, classes, and modules
- Keep functions small and focused on a single task
- Use type hints where appropriate
