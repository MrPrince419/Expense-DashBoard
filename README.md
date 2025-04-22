# Expense Tracker

A data-driven financial management application for analytics professionals. Streamline expense tracking, visualization, and financial insights through an intuitive Streamlit interface.

![Expense Tracker](asset/landing%20page.png)

## Overview

Expense Tracker empowers data analysts to transform raw financial data into actionable insights. The application handles multi-format data imports, automates column mapping, and generates interactive visualizations to reveal spending patterns and financial trends.

## Key Features

- **Data Import & Processing**
  - Support for CSV, Excel, JSON, TXT, Parquet, PDF, and ZIP formats
  - Intelligent column mapping with fuzzy matching
  - Automated data cleaning and standardization
  - Duplicate transaction detection using similarity algorithms

- **Analytics & Visualization**
  - Comprehensive spending pattern analysis
  - Time series visualization of income vs expenses
  - Category-based expenditure breakdowns
  - Anomaly detection and trend identification

- **Data Management**
  - Secure user-specific data storage
  - Cross-session data persistence
  - Export capabilities (CSV/Excel)
  - Optional data profiling reports

- **Administrative Tools**
  - User activity monitoring
  - System usage analytics
  - Data quality metrics
  - Export statistics for external analysis

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/expense-tracker.git
cd expense-tracker

# Install dependencies
pip install -r requirements.txt

# Launch the application
streamlit run app.py
```

### Login Credentials

- **Regular User**: Create an account via the signup page
- **Admin Access**: 
  - Email: admin@example.com
  - Password: Admin@123456

## Data Analysis Workflow

### 1. Data Import

Upload financial data through the intuitive interface:

- **Auto-Detection**: The system intelligently maps columns from various formats
- **Data Validation**: Automatic checks for data integrity and completeness
- **Sample Data**: Test functionality with built-in sample datasets

![Upload Interface](asset/upload%20page%20%231.png)

### 2. Data Exploration & Cleaning

- **Data Preview**: Examine uploaded transactions before processing
- **Duplicate Detection**: Identify and manage duplicate entries
- **Data Profiling**: Generate comprehensive dataset statistics (requires optional dependencies)

### 3. Analysis & Visualization

Access the Dashboard to reveal financial insights:

- **Key Metrics**: Track spending, income, and savings rates
- **Temporal Analysis**: Visualize financial patterns over time
- **Categorical Breakdown**: Identify major spending categories
- **Comparative Analysis**: Benchmark current vs. historical data

![Dashboard Analytics](asset/dashboard%20page%20%232.png)

### 4. Export & Sharing

- Export processed data in preferred formats
- Download visualization images for reports
- Save analysis state for future sessions

## Advanced Features

### PDF Data Extraction

Extract transaction data directly from bank statements and receipts using:
- Table detection algorithms
- Pattern recognition for transaction data
- Intelligent text processing

### Data Profiling Integration

Install optional dependencies for enhanced analysis:
```bash
pip install ydata-profiling pandas-profiling sweetviz
```

### Fuzzy Matching for Data Quality

Improve data consistency with fuzzy matching:
```bash
pip install rapidfuzz
```

## Technical Architecture

- **Data Processing**: Pandas for dataframe operations
- **Visualization**: Plotly and Altair for interactive charts
- **Authentication**: Custom user management with secure password hashing
- **Storage**: JSON-based file storage with transaction history

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing dependencies | Run `pip install -r requirements.txt` |
| File upload errors | Verify file format compatibility |
| Performance issues | Consider data sampling for large datasets |
| Corrupted user data | Delete user-specific JSON files to reset |

## Security

- Password hashing using pbkdf2_sha256
- Secret questions with SHA-256 answer hashing
- Local data storage with minimal PII collection
- Input validation against injection attacks

## For Developers

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

---

*Last updated: April 21, 2025*

For support: [![Email](https://img.shields.io/badge/Email-Support-blue?style=flat-square&logo=gmail)](mailto:PrinceUwagboe44@outlook.com)