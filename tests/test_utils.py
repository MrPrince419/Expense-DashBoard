import pytest
import pandas as pd
from utils import load_user_data, save_user_data, get_user_file

@pytest.fixture
def sample_data():
    return pd.DataFrame([
        {"Date": "2023-01-01", "Name": "Test", "Amount": 100.0, "Category": "Food"},
        {"Date": "2023-01-02", "Name": "Sample", "Amount": 200.0, "Category": "Transport"}
    ])

def test_save_and_load_user_data(sample_data):
    username = "test_user"
    save_user_data(username, sample_data)
    loaded_data = load_user_data(username)
    pd.testing.assert_frame_equal(sample_data, loaded_data)

def test_load_user_data_empty():
    username = "nonexistent_user"
    data = load_user_data(username)
    assert data.empty
    assert list(data.columns) == ["Date", "Name", "Amount", "Category"]
