import sys
from unittest.mock import MagicMock

# Localized mocking for this test module to avoid environment issues
# and ensure we don't affect other tests.
# We mock the external dependencies of scripts.scraper only for the duration of this import.
with MagicMock() as mock_httpx, MagicMock() as mock_bs4:
    sys.modules["httpx"] = mock_httpx
    sys.modules["bs4"] = mock_bs4
    sys.modules["lxml"] = MagicMock()
    from scripts.scraper import infer_category

import pytest

@pytest.mark.parametrize("title, expected_category", [
    ("The Indian Penal Code, 1860", "criminal"),
    ("Code of Civil Procedure, 1908", "civil"),
    ("The Constitution of India", "constitutional"),
    ("Companies Act, 2013", "commercial"),
    ("Factories Act, 1948", "labour"),
    ("Income Tax Act, 1961", "tax"),
    ("Hindu Marriage Act, 1955", "family"),
    ("Transfer of Property Act, 1882", "property"),
    ("Random Act Name", "misc"),
    ("INDIAN PENAL CODE", "criminal"),
    ("Specific Relief Act", "civil"),
])
def test_infer_category(title, expected_category):
    assert infer_category(title) == expected_category
