# Expense Tracker Dashboard

## Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Data Sources](#data-sources)
- [Tools and Technologies](#tools-and-technologies)
- [Methodology](#methodology)
  - [Data Cleaning and Preprocessing](#data-cleaning-and-preprocessing)
  - [Exploratory Data Analysis (EDA)](#exploratory-data-analysis-eda)
  - [Feature Engineering](#feature-engineering)
  - [Modeling Techniques](#modeling-techniques)
  - [Validation Methods](#validation-methods)
- [Results and Insights](#results-and-insights)
- [Conclusion and Recommendations](#conclusion-and-recommendations)
- [Challenges and Limitations](#challenges-and-limitations)
- [Future Work](#future-work)
- [Appendices](#appendices)
  - [Data Dictionary](#data-dictionary)
  - [Code Repository & Key Files](#code-repository--key-files)
  - [References](#references)

---

## Project Overview

**Expense Tracker Dashboard** is a data-driven financial management application designed for analytics professionals and individuals. It streamlines expense tracking, automates data cleaning, and delivers interactive visualizations to help users make informed financial decisions. Built with Streamlit, it supports multi-format data imports, secure user management, and actionable insights through a modern dashboard interface.

![Landing Page](asset/landing%20page.png)

---

## Problem Statement

Managing personal and business finances is often hindered by disparate data sources, inconsistent formats, and a lack of actionable insights. This project addresses the need for a unified platform that automates the ingestion, cleaning, and analysis of financial transactions, enabling users to identify spending patterns, detect anomalies, and optimize their financial health.

---

## Data Sources

- **Sample Transactions:**
  - [Sample_Transactions.csv](./Sample_Transactions.csv)
  - [sample_data/sample_transactions.csv](./sample_data/sample_transactions.csv)
- **User-Uploaded Data:** Supports CSV, Excel, JSON, TXT, Parquet, PDF, and ZIP formats.
- **Manual Entry:** Users can input transactions directly via the app interface.

---

## Tools and Technologies

- **Programming Language:** Python 3.8+
- **Libraries & Frameworks:**
  - [Streamlit](https://streamlit.io/) (UI & app framework)
  - [Pandas](https://pandas.pydata.org/) (data processing)
  - [NumPy](https://numpy.org/) (numerical operations)
  - [Plotly](https://plotly.com/python/) & [Altair](https://altair-viz.github.io/) (visualization)
  - [Openpyxl](https://openpyxl.readthedocs.io/) & [XlsxWriter](https://xlsxwriter.readthedocs.io/) (Excel support)
  - [PyArrow](https://arrow.apache.org/) (Parquet support)
  - [PDFPlumber](https://github.com/jsvine/pdfplumber) & [Tabula-py](https://tabula-py.readthedocs.io/) (PDF extraction)
  - [RapidFuzz](https://maxbachmann.github.io/RapidFuzz/) (fuzzy matching)
  - [YData-Profiling](https://ydata-profiling.ydata.ai/docs/latest/) & [Sweetviz](https://github.com/fbdesignpro/sweetviz) (data profiling)
  - [Passlib](https://passlib.readthedocs.io/) (password hashing)
- **Other Tools:**
  - [pytest](https://docs.pytest.org/) (testing)
  - [Git](https://git-scm.com/) (version control)

See [requirements.txt](./requirements.txt) for the full list.

---

## Methodology

### Data Cleaning and Preprocessing
- Automated column mapping using fuzzy matching for diverse file formats ([pages/1_Upload.py](./pages/1_Upload.py)).
- Removal of duplicates and standardization of date, amount, and category fields.
- Handling missing values and outlier detection.
- Data validation to ensure integrity and completeness ([utils.py](./utils.py)).

### Exploratory Data Analysis (EDA)
- Summary statistics of income and expenses.
- Visualization of spending trends over time.
- Category-wise expenditure breakdown.
- Detection of unusual transactions and anomalies ([pages/2_Dashboard.py](./pages/2_Dashboard.py)).

### Feature Engineering
- Creation of new features such as:
  - Monthly savings rate
  - Rolling averages of expenses
  - Categorization of merchants and transaction types

### Modeling Techniques
- Time series analysis for trend detection.
- Clustering for identifying spending patterns.
- Anomaly detection using statistical thresholds.

### Validation Methods
- Cross-validation for model robustness.
- Manual review of flagged anomalies.
- Comparison with historical data for consistency.

---

## Results and Insights

- **Key Findings:**
  - Identified top spending categories and peak expense periods.
  - Detected duplicate and anomalous transactions, reducing data errors.
  - Visualized monthly savings trends, highlighting opportunities for budget optimization.
- **Visualizations:**
  - Interactive dashboards for income vs. expenses.
  - Pie charts for category breakdowns.
  - Time series plots for trend analysis.

### Dashboard & Admin Panel Visuals

#### Dashboard
![Dashboard 1](asset/dashboard%20page%20%231.png)
![Dashboard 2](asset/dashboard%20page%20%232.png)
![Dashboard 3](asset/dashboard%20page%20%233.png)
![Dashboard 4](asset/dashboard%20page%20%234.png)

#### Upload Interface
![Upload 1](asset/upload%20page%20%231.png)
![Upload 2](asset/upload%20page%20%232.png)
![Upload 3](asset/upload%20page%20%233.png)

#### Admin Panel
![Admin Panel 1](asset/admin%20panel%20%231.png)
![Admin Panel 2](asset/admin%20panel%20%232.png)
![Admin Panel 3](asset/admin%20panel%20%233.png)
![Admin Panel 4](asset/admin%20panel%20%234.png)
![Admin Panel 5](asset/admin%20panel%20%235.png)

---

## Conclusion and Recommendations

The Expense Tracker Dashboard automates financial data analysis, providing users with clear, actionable insights. Users are encouraged to regularly review their dashboards, set savings goals, and investigate flagged anomalies to maintain financial health.

---

## Challenges and Limitations

- **Data Quality:** Inconsistent formats and missing values in user-uploaded files.
- **PDF Extraction:** Variability in bank statement layouts affects extraction accuracy.
- **Scalability:** Performance may degrade with very large datasets.
- **User Privacy:** Local storage is used; cloud integration is not implemented.

---

## Future Work

- Integrate with banking APIs for real-time data import.
- Enhance anomaly detection with machine learning models.
- Add support for multi-currency and investment tracking.
- Deploy as a web application with user authentication and cloud storage.

---

## Appendices

### Data Dictionary

| Variable   | Description                                 |
|------------|---------------------------------------------|
| Date       | Transaction date (YYYY-MM-DD)               |
| Name       | Merchant or transaction details             |
| Category   | Expense category (e.g., Food, Utilities)    |
| Amount     | Transaction amount (positive/negative)      |
| Type       | Income or Expense (if present)              |

### Code Repository & Key Files

- **Repository:** [https://github.com/PrinceUwagboe/expense-tracker-dashboard](https://github.com/PrinceUwagboe/expense-tracker-dashboard)
- **App Entry Point:** [app.py](./app.py)
- **Authentication Module:** [auth.py](./auth.py)
- **Utilities:** [utils.py](./utils.py)
- **Upload Page:** [pages/1_Upload.py](./pages/1_Upload.py)
- **Dashboard Page:** [pages/2_Dashboard.py](./pages/2_Dashboard.py)
- **Admin Panel:** [pages/admin_panel.py](./pages/admin_panel.py)
- **Sample Data:** [Sample_Transactions.csv](./Sample_Transactions.csv), [sample_data/sample_transactions.csv](./sample_data/sample_transactions.csv)
- **User Data Directory:** [user_data/](./user_data/)
- **Tests:** [tests/](./tests/)
- **Admin Credentials Backup:** [admin_credentials_backup.json](./admin_credentials_backup.json)
- **Contributing Guide:** [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Requirements:** [requirements.txt](./requirements.txt)

### References

- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [ydata-profiling](https://ydata-profiling.ydata.ai/docs/latest/)
- [Sweetviz](https://github.com/fbdesignpro/sweetviz)
- [RapidFuzz](https://maxbachmann.github.io/RapidFuzz/)

---

*For support, contact [PrinceUwagboe44@outlook.com](mailto:PrinceUwagboe44@outlook.com)*
