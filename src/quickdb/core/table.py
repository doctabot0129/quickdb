from typing import List

import pandas as pd
import sqlalchemy as sa


class SQLTable:
    def __init__(self, connection: sa.Connection, database_name: str, table_name: str) -> None:
        self.connection: sa.Connection = connection
        self.database_name = database_name
        self.table_name = table_name
        self.all_columns_list = self.get_column_list()
        self.load_columns(column_list=self.all_columns_list)

    def get_column_list(self) -> List[str]:
        result = self.connection.execute(
            sa.text(
                f'SELECT COLUMN_NAME FROM {self.database_name}.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = :table_name'
            ).bindparams(table_name=self.table_name)
        )
        return [column[0] for column in result.fetchall()]

    def load_column(self, column_name: str):
        if column_name in self.all_columns_list:
            setattr(self, column_name, column_name)
        else:
            print(f'Column {column_name} not found')

    def load_columns(self, column_list: List[str] | None = None):
        for column in (column_list or []):
            self.load_column(column_name=column)

    def _table_clause(self) -> sa.TextClause:
        if self.connection.dialect.name == 'mssql':
            return sa.text(f'{self.database_name}.dbo.{self.table_name}')
        return sa.text(f'{self.database_name}.{self.table_name}')

    def limited_query(
        self, fields: List[str] | None = None, where: List[str] | None = None, limit: int = 10
    ) -> pd.DataFrame:
        cols = [sa.literal_column(f) for f in (fields or ['*'])]
        stmt = sa.select(*cols).select_from(self._table_clause()).limit(limit)
        if where:
            stmt = stmt.where(sa.and_(*[sa.text(c) for c in where]))
        return pd.read_sql_query(stmt, self.connection)
