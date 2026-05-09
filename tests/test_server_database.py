from unittest.mock import MagicMock, patch

import pytest

from quickdb.core.database import SQLDatabase
from quickdb.core.server import MariaDBServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_classes(table_names: list[str]) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__.side_effect = lambda k: (
        MagicMock(name=k) if k in table_names else (_ for _ in ()).throw(KeyError(k))
    )
    mock.keys.return_value = table_names
    return mock


def _make_db(table_names: list[str] | None = None, prepared: bool = True) -> SQLDatabase:
    db = object.__new__(SQLDatabase)
    db.database_name = 'testdb'
    db._prepared = prepared
    db._base = MagicMock()
    db._base.classes = _make_mock_classes(table_names or [])
    return db


def _make_server(db_names: list[str] | None = None) -> MagicMock:
    server = MagicMock(spec=MariaDBServer)
    databases = {name: _make_db() for name in (db_names or ['mydb'])}
    server.__dict__['_databases'] = databases
    return server


# ---------------------------------------------------------------------------
# SQLDatabase.__getattr__
# ---------------------------------------------------------------------------

def test_database_getattr_returns_table_when_prepared():
    db = _make_db(['accounts'])
    result = db.accounts
    db._base.classes.__getitem__.assert_called_once_with('accounts')


def test_database_getattr_raises_attribute_error_for_private_name():
    db = _make_db()
    with pytest.raises(AttributeError):
        _ = db._private


def test_database_getattr_raises_attribute_error_for_missing_table():
    db = _make_db(['accounts'])
    with pytest.raises(AttributeError, match="Table 'orders' not found in database 'testdb'"):
        _ = db.orders


def test_database_getattr_triggers_prepare_when_not_prepared():
    db = _make_db(prepared=False)
    db.prepare = MagicMock(side_effect=lambda: setattr(db, '_prepared', True))
    db._base.classes = _make_mock_classes(['accounts'])
    _ = db.accounts
    db.prepare.assert_called_once()


def test_database_getattr_does_not_prepare_when_already_prepared():
    db = _make_db(['accounts'])
    db.prepare = MagicMock()
    _ = db.accounts
    db.prepare.assert_not_called()


# ---------------------------------------------------------------------------
# Server.__getattr__
# ---------------------------------------------------------------------------

def _bare_server(db_names: list[str]) -> MariaDBServer:
    inst = object.__new__(MariaDBServer)
    inst.__dict__['_databases'] = {name: MagicMock() for name in db_names}
    return inst


def test_server_getattr_returns_database():
    server = _bare_server(['mydb'])
    result = server.mydb
    assert result is server.__dict__['_databases']['mydb']


def test_server_getattr_raises_for_private_name():
    server = _bare_server([])
    with pytest.raises(AttributeError):
        _ = server._private


def test_server_getattr_raises_for_missing_database():
    server = _bare_server(['mydb'])
    with pytest.raises(AttributeError, match="Database 'other' not found on server"):
        _ = server.other


def test_server_getattr_raises_when_databases_not_initialised():
    server = object.__new__(MariaDBServer)
    with pytest.raises(AttributeError):
        _ = server.anything
