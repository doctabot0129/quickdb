from typing import List

import sqlalchemy as sa

from quickdb.core.table import SQLTable


class SQLDatabase:
    def __init__(
        self, connection: sa.Connection, database_name: str, full_init: bool = False
    ) -> None:
        self.connection: sa.Connection = connection
        self.database_name: str = database_name
        self.all_tables_list: List[str] = self.load_table_list()
        if full_init:
            self.load_tables(table_list=self.all_tables_list)

    def load_table_list(self) -> List[str]:
        try:
            result = self.connection.execute(
                sa.text(f'SELECT name FROM {self.database_name}.sys.tables')
            )
            return [table[0] for table in result.fetchall()]
        except Exception:
            print(f'Error unable to connect to {self.database_name}')
            return []

    def load_table(self, table_name: str) -> None:
        if table_name in self.all_tables_list:
            setattr(
                self,
                table_name,
                SQLTable(
                    connection=self.connection,
                    database_name=self.database_name,
                    table_name=table_name,
                ),
            )
        else:
            print(f'Table {table_name} not found')

    def load_tables(self, table_list: List[str] | None = None) -> None:
        for table in (table_list or []):
            self.load_table(table_name=table)
