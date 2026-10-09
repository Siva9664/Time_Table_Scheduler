import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.database import (
    close_mongo_connection,
    get_db,
    init_indexes,
    initialize_tenant_db,
)


class TestDatabaseIndexInitialization:
    def test_init_indexes_creates_all_expected_unique_indexes(self):
        mock_db = MagicMock()
        mock_collections = {}

        def get_col(name):
            if name not in mock_collections:
                mock_collections[name] = MagicMock()
            return mock_collections[name]

        mock_db.__getitem__.side_effect = get_col

        init_indexes(mock_db)

        # Check unique indexes created
        mock_collections["users"].create_index.assert_any_call("username", unique=True)
        mock_collections["users"].create_index.assert_any_call("email", unique=True)
        mock_collections["departments"].create_index.assert_called_with("code", unique=True)
        mock_collections["subjects"].create_index.assert_called_with("code", unique=True)
        mock_collections["faculty"].create_index.assert_called_with("email", unique=True, sparse=True)
        mock_collections["ingestion_review_sessions"].create_index.assert_called_with("session_id", unique=True)
        mock_collections["ingestion_history"].create_index.assert_called_with("session_id", unique=True)

    def test_init_indexes_swallows_exception_safely(self):
        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = Exception("Mongo connection refused")

        # Must not raise an unhandled exception
        init_indexes(mock_db)


class TestTenantDatabaseInitialization:
    def test_initialize_tenant_db_creates_collections_if_missing(self):
        mock_client = MagicMock()
        mock_tenant_db = MagicMock()
        mock_tenant_db.list_collection_names.return_value = ["departments"]
        mock_client.__getitem__.return_value = mock_tenant_db

        with patch("app.database.database.get_client", return_value=mock_client):
            initialize_tenant_db("timetable_db_cse")

            expected_missing = [
                "batches",
                "rooms",
                "classes",
                "subjects",
                "faculty",
                "timetables",
            ]
            for col in expected_missing:
                mock_tenant_db.create_collection.assert_any_call(col)


class TestConnectionTeardownAndDependency:
    def test_close_mongo_connection_resets_client(self):
        mock_client = MagicMock()
        with patch("app.database.database._client", mock_client):
            close_mongo_connection()
            mock_client.close.assert_called_once()

    def test_get_db_yields_database(self):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch("app.database.database.get_client", return_value=mock_client):
            db_generator = get_db()
            yielded_db = next(db_generator)
            assert yielded_db == mock_db
