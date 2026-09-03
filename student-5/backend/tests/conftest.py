import os
import sys

import pytest

# Make app.py / db_client.py importable when pytest is invoked from the
# repository root.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402

# A hostname that does not resolve, so an un-mocked request can never
# accidentally reach a real service.
DATABASE_API_URL = "http://test-database:8080"


@pytest.fixture
def database_url():
    return DATABASE_API_URL


@pytest.fixture
def client(database_url):
    app = create_app({"DATABASE_API_URL": database_url})
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
