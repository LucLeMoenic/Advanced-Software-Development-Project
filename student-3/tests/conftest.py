import importlib.util
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT3_DIR = os.path.dirname(TESTS_DIR)
BACKEND_DIR = os.path.join(STUDENT3_DIR, "backend")
DATABASE_DIR = os.path.join(STUDENT3_DIR, "database")

# Both service directories are added once so their modules (db,
# database_client, ...) can import each other's siblings with plain
# top-level imports, exactly like they do inside their own containers.
for directory in (BACKEND_DIR, DATABASE_DIR):
    if directory not in sys.path:
        sys.path.insert(0, directory)


def _load_module_fresh(name, path):
    """Loads a module under a unique name, bypassing sys.modules caching.

    Both services ship an app.py, so a plain `import app` would silently
    return whichever one was imported first. Loading each under a distinct
    name lets a single test session exercise both Flask apps.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database_client(tmp_path, monkeypatch):
    """A Flask test client for the student-3 database microservice, backed
    by a fresh temp SQLite file per test."""
    db_path = tmp_path / "attractions_test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    db_module = _load_module_fresh("student3_test_db", os.path.join(DATABASE_DIR, "db.py"))
    db_module.ensure_schema()

    database_app_module = _load_module_fresh(
        "student3_database_app", os.path.join(DATABASE_DIR, "app.py")
    )
    with database_app_module.app.test_client() as client:
        yield client


@pytest.fixture
def backend_client(monkeypatch):
    """A Flask test client for the student-3 backend, with no live
    dependency on the database service - tests mock database_client
    as needed."""
    backend_app_module = _load_module_fresh(
        "student3_backend_app", os.path.join(BACKEND_DIR, "app.py")
    )
    with backend_app_module.app.test_client() as client:
        yield client
