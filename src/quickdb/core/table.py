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
                f"SELECT COLUMN_NAME FROM {self.database_name}.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{self.table_name}'"
            )
        )
        return [column[0] for column in result.fetchall()]

    def load_column(self, column_name: str):
        if column_name in self.all_columns_list:
            setattr(self, column_name, column_name)
        else:
            print(f'Column {column_name} not found')

    def load_columns(self, column_list: List[str] = []):
        for column in column_list:
            self.load_column(column_name=column)

    def limited_query(
        self, fields: List[str] = ['*'], where: List[str] = [], limit: int = 10
    ) -> pd.DataFrame:

        fields = ', '.join(fields)
        where = ' AND '.join(where)
        if where:
            where = f'WHERE {where}'
        limit = f'TOP {limit}'
        query_str = (
            f'SELECT {limit} {fields} FROM {self.database_name}.dbo.{self.table_name} {where}'
        )

        return pd.read_sql_query(query_str, self.connection)
