import os
import sys

import pytest

# Make app.py importable when pytest is invoked from the repository root.
DATABASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DATABASE_DIR not in sys.path:
    sys.path.insert(0, DATABASE_DIR)

from app import create_app  # noqa: E402


@pytest.fixture
def database_path(tmp_path):
    """A throwaway SQLite file so tests never touch the real /data volume."""
    return str(tmp_path / "logistics.db")


@pytest.fixture
def client(database_path):
    app = create_app(database_path=database_path)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
