from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from quickdb.core.database import SQLDatabase
from quickdb.core.server import MariaDBServer, Server

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
    _ = db.accounts
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


# ---------------------------------------------------------------------------
# Server.sanitize_db_type
# ---------------------------------------------------------------------------

def test_sanitize_db_type_lowercases():
    assert Server.sanitize_db_type('MariaDB') == 'mariadb'


def test_sanitize_db_type_strips_hyphens():
    assert Server.sanitize_db_type('maria-db') == 'mariadb'


def test_sanitize_db_type_strips_underscores():
    assert Server.sanitize_db_type('my_sql') == 'mysql'


def test_sanitize_db_type_strips_spaces():
    assert Server.sanitize_db_type('maria db') == 'mariadb'


# ---------------------------------------------------------------------------
# Server.driver_name
# ---------------------------------------------------------------------------

def _server_with_db_type(db_type: str) -> Server:
    inst = object.__new__(Server)
    inst.__dict__['db_type'] = db_type
    return inst


def test_driver_name_raises_value_error_for_unknown_type():
    server = _server_with_db_type('oracle')
    with pytest.raises(ValueError, match="Unsupported db_type 'oracle'"):
        _ = server.driver_name


def test_driver_name_returns_correct_driver_for_mariadb():
    server = _server_with_db_type('mariadb')
    assert server.driver_name == 'mysql+pymysql'


def test_driver_name_returns_correct_driver_for_mssql():
    server = _server_with_db_type('mssql')
    assert server.driver_name == 'mssql+pymssql'


# ---------------------------------------------------------------------------
# Server.get_available_dbs
# ---------------------------------------------------------------------------

def _server_with_connection(db_type: str, execute_side_effect=None) -> Server:
    inst = object.__new__(Server)
    inst.__dict__['db_type'] = db_type
    inst.connection = MagicMock()
    if execute_side_effect:
        inst.connection.execute.side_effect = execute_side_effect
    return inst


def test_get_available_dbs_reraises_sqlalchemy_error():
    server = _server_with_connection('mariadb', execute_side_effect=SQLAlchemyError('connection refused'))
    with pytest.raises(SQLAlchemyError):
        server.get_available_dbs()
