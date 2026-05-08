from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import pandas as pd
from urllib.parse import quote_plus
import sqlalchemy as sa
from dotenv import load_dotenv

from quickdb.core.database import SQLDatabase
from quickdb.core.query_mgr import SQLQueryManager
from quickdb.core.utils import resolve_project_root

load_dotenv() 


class Server(ABC):
    def __init__(
        self,
        server_name: str,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        database: str | None = None,
        full_init: bool = False,
    ) -> None:
        self.conn_string: sa.URL = sa.URL.create(
            drivername=self.driver_name,
            host=server_name,
            username=username,
            password=quote_plus(password, safe='/:?=&,') if password else None,
            port=port,
            database=database,
        )
        self.engine: sa.Engine = sa.create_engine(self.conn_string)
        self.connection: sa.Connection = self.engine.connect()
        self.all_databases_list = self.load_database_list()
        self.init_query_dirs()
        
        if full_init:
            self.load_databases(self.my_databases, full_init=True)
            
    def init_query_dirs(self):
        self.test_query_dir = resolve_project_root() / 'queries' / 'test'
        self.query_dir = resolve_project_root() / 'queries'
        self.test_query_dir.mkdir(exist_ok=True)
        self.query_dir.mkdir(exist_ok=True)

    @property
    @abstractmethod
    def driver_name(self) -> str:
        pass

    @property
    def my_databases(self) -> List[str]:
        return []

    @abstractmethod
    def load_database_list(self) -> List[str]:
        """Gathers name list of all databases on the server

        Returns:
            List[str]: List of database names
        """
        pass

    def load_database(self, database_name: str, full_init: bool = False) -> None:
        """Loads a single database onto the server object

        Args:
            database_name (str): Database name to load
        """
        try:
            setattr(
                self,
                database_name,
                SQLDatabase(
                    connection=self.connection,
                    database_name=database_name,
                    full_init=full_init,
                ),
            )
        except Exception:
            print(f'Database {database_name} not found')

    def load_databases(self, database_list: List[str] = [], full_init: bool = False) -> None:
        for database in database_list:
            self.load_database(database_name=database, full_init=full_init)

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

    def load_database_list(self) -> List[str]:
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

    def load_database_list(self) -> List[str]:
        """Gathers name list of all databases on the server

        Returns:
            List[str]: List of database names
        """

        result = self.connection.execute(sa.text('SELECT name FROM sys.databases'))
        return [database[0] for database in result.fetchall()]

