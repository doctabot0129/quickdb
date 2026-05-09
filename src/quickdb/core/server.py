import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Self

import pandas as pd
import sqlalchemy as sa

from quickdb.core.database import SQLDatabase
from quickdb.core.query_mgr import SQLQueryManager
from quickdb.core.utils import resolve_project_root

logger = logging.getLogger(__name__)


class Server(ABC):
    def __init__(
        self,
        server_name: str,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        database: str | None = None,
        cache_all: bool = False,
    ) -> None:

        self.conn_string: sa.URL = sa.URL.create(
            drivername=self.driver_name,
            host=server_name,
            username=username,
            password=password,
            port=port,
            database=database,
        )
        self.engine: sa.Engine = sa.create_engine(self.conn_string)
        self.connection: sa.Connection = self.engine.connect()
        self.init_query_dirs()

        self._cache_all = cache_all
        self._databases = {}

        self._initialize_dbs()

    def init_query_dirs(self):
        self.query_dir = resolve_project_root() / 'queries' / 'saved'
        self.test_query_dir = resolve_project_root() / 'queries' / 'test'
        self.query_dir.mkdir(exist_ok=True)
        self.test_query_dir.mkdir(exist_ok=True)

    @property
    @abstractmethod
    def driver_name(self) -> str:
        pass

    @property
    def my_databases(self) -> List[str]:
        return [self.engine.url.database] if self.engine.url.database else []

    @abstractmethod
    def get_available_dbs(self) -> List[str]:
        """Gathers name list of all databases on the server

        Returns:
            List[str]: List of database names
        """
        pass

    def _set_db_key(self, database_name: str, full_init: bool = False) -> None:
        """Loads a single database onto the server object

        Args:
            database_name (str): Database name to load
        """
        if database_name not in self._databases:
            self._databases[database_name] = SQLDatabase(
                server=self,
                database_name=database_name,
                full_init=full_init,
            )

    def _initialize_dbs(self) -> None:
        available_dbs = self.get_available_dbs()

        for db in self.my_databases:
            if db in available_dbs:
                self._set_db_key(db, full_init=True)
            else:
                logger.warning('Database %r not found in available databases: %r', db, available_dbs)
        for db in set(available_dbs) - set(self.my_databases):
            self._set_db_key(db, full_init=self._cache_all)

    def __getattr__(self, name: str) -> 'SQLDatabase':
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self.__dict__['_databases'][name]
        except KeyError:
            raise AttributeError(f"Database {name!r} not found on server")

    def close(self) -> None:
        self.connection.close()
        self.engine.dispose()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_query_mgr(self, sql_file_path: Path) -> SQLQueryManager:
        query_manager = SQLQueryManager(sql_file_path)
        return query_manager

    def query_mgr_to_pandas(self, query_manager: SQLQueryManager) -> pd.DataFrame:
        return pd.read_sql_query(query_manager.get_query(), self.connection)

    def query_to_pandas(self, sql_file_path: Path) -> pd.DataFrame:
        query_manager = self.get_query_mgr(sql_file_path)
        # sql_str = read_query(sql_file_path)
        return self.query_mgr_to_pandas(query_manager)

class MariaDBServer(Server):
    @property
    def driver_name(self) -> str:
        return 'mysql+pymysql'

    def get_available_dbs(self) -> List[str]:
        """Gathers name list of all databases on the server

        Returns:
            List[str]: List of database names
        """

        result = self.connection.execute(sa.text('SHOW DATABASES'))
        return [database[0] for database in result.fetchall()]


class SQLServer(Server):
    @property
    def driver_name(self) -> str:
        return 'mssql+pymssql'

    def get_available_dbs(self) -> List[str]:
        """Gathers name list of all databases on the server

        Returns:
            List[str]: List of database names
        """

        result = self.connection.execute(sa.text('SELECT name FROM sys.databases'))
        return [database[0] for database in result.fetchall()]

if __name__ == '__main__':
    import os

    from dotenv import load_dotenv
    load_dotenv()
    with MariaDBServer(
        server_name="crm-mysql-01.procarerx.com",
        username=os.getenv('CRM_MY_SQL_USERNAME'),
        password=os.getenv('CRM_MY_SQL_PASSWORD'),
        port=int(os.getenv('CRM_MY_SQL_PORT', 3306)),
    ) as server:
        print(server.get_available_dbs())
