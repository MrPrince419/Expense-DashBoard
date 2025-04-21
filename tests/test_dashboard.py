import pytest
import pandas as pd
from pages.2_Dashboard import calculate_metrics

@pytest.fixture
def sample_transactions():
    return pd.DataFrame([
        {"Type": "Income", "Amount": 1000.0},
        {"Type": "Expense", "Amount": 500.0},
        {"Type": "Income", "Amount": 200.0},
        {"Type": "Expense", "Amount": 300.0}
    ])

def test_calculate_metrics(sample_transactions):
    st = {"transactions": sample_transactions}
    total_income, total_expenses, net_savings = calculate_metrics(st)
    assert total_income == 1200.0
    assert total_expenses == 800.0
    assert net_savings == 400.0

def test_calculate_metrics_empty():
    st = {"transactions": pd.DataFrame(columns=["Type", "Amount"])}
    total_income, total_expenses, net_savings = calculate_metrics(st)
    assert total_income == 0
    assert total_expenses == 0
    assert net_savings == 0
