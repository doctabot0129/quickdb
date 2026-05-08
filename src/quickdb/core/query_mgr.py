import re
from pathlib import Path
from typing import Dict, List

from quickdb.core.utils import read_query


class SQLQueryManager:
    def __init__(self, query_path: Path) -> None:
        self.base_query = read_query(query_path)

    def _find_clause_positions(self) -> Dict[str, int]:
        """
        Find positions of major SQL clauses in the query.
        Returns a dictionary of clause positions, with -1 if not found.
        """
        clause_patterns = {
            'where': r'\bWHERE\b',
            'group_by': r'\bGROUP\s+BY\b',
            'order_by': r'\bORDER\s+BY\b',
            'having': r'\bHAVING\b',
        }

        positions = {}
        query_upper = self.base_query.upper()

        for clause, pattern in clause_patterns.items():
            match = re.search(pattern, query_upper)
            positions[clause] = match.start() if match else -1

        return positions

    def change_db(self, database_name: str) -> 'SQLQueryManager':
        """
        Replace the database name in the FROM clause.

        Args:
            database_name: The new database name to use
        """
        pattern = r'\bFROM\s+([a-zA-Z0-9_]+)\.dbo\b'
        match = re.search(pattern, self.base_query, re.IGNORECASE)

        if not match:
            raise ValueError('No database name found in the FROM clause')

        old_db_name = match.group(1)
        self.base_query = re.sub(
            rf'\bFROM\s+{old_db_name}\.dbo\b',
            f'FROM {database_name}.dbo',
            self.base_query,
            flags=re.IGNORECASE,
        )

        return self

    def add_where_clause(self, condition: str) -> 'SQLQueryManager':
        """
        Add a WHERE clause to the query if none exists, or add condition with AND if it does.

        Args:
            condition: The WHERE condition to add
        """
        positions = self._find_clause_positions()

        if positions['where'] != -1:
            # WHERE exists, add condition with AND
            self.base_query = self.base_query.replace('WHERE', f'WHERE {condition} AND ')
        else:
            # Find the first subsequent clause to insert before
            next_clauses = ['group_by', 'having', 'order_by']
            insert_positions = [pos for clause in next_clauses if (pos := positions[clause]) != -1]

            if insert_positions:
                # Insert before the first found clause
                pos = min(insert_positions)
                self.base_query = (
                    f'{self.base_query[:pos]}WHERE {condition} \n{self.base_query[pos:]}'
                )
            else:
                # No subsequent clauses, append to end
                self.base_query += f'\nWHERE {condition}'

        return self

    def add_or_clause(self, condition: str) -> 'SQLQueryManager':
        """
        Add an OR condition to an existing WHERE clause.

        Args:
            condition: The condition to add with OR
        """
        positions = self._find_clause_positions()

        if positions['where'] == -1:
            raise ValueError('Cannot add OR condition without existing WHERE clause')

        # Find the end of the current WHERE clause
        next_clauses = ['group_by', 'having', 'order_by']
        next_positions = [pos for clause in next_clauses if (pos := positions[clause]) != -1]

        if next_positions:
            # Insert before the next clause
            pos = min(next_positions)
            self.base_query = f'{self.base_query[:pos]} OR {condition}{self.base_query[pos:]}'
        else:
            # No subsequent clauses, append to end of WHERE
            self.base_query += f' OR {condition}'

        return self

    def add_group_by(self, columns: List[str]) -> 'SQLQueryManager':
        """Add GROUP BY clause or append to existing one."""
        positions = self._find_clause_positions()
        group_by_clause = ', '.join(columns)

        if positions['group_by'] != -1:
            # Find the end of the GROUP BY clause
            next_clauses = ['having', 'order_by']
            next_positions = [pos for clause in next_clauses if (pos := positions[clause]) != -1]

            if next_positions:
                insert_pos = min(next_positions)
                self.base_query = (
                    f'{self.base_query[:insert_pos]}, '
                    f'{group_by_clause}'
                    f'{self.base_query[insert_pos:]}'
                )
            else:
                self.base_query += f', {group_by_clause}'
        else:
            # Find position to insert GROUP BY
            if positions['order_by'] != -1:
                # Insert before ORDER BY
                pos = positions['order_by']
                self.base_query = (
                    f'{self.base_query[:pos]}GROUP BY {group_by_clause} \n{self.base_query[pos:]}'
                )
            else:
                # Append to end
                self.base_query += f'\nGROUP BY {group_by_clause}'

        return self

    def add_order_by(self, columns: List[str]) -> 'SQLQueryManager':
        """Add ORDER BY clause or append to existing one."""
        positions = self._find_clause_positions()
        order_by_clause = ', '.join(columns)

        if positions['order_by'] != -1:
            # ORDER BY exists, append columns
            self.base_query += f', {order_by_clause}'
        else:
            # Add new ORDER BY clause at the end
            self.base_query += f'\nORDER BY {order_by_clause}'

        return self

    def get_query(self) -> str:
        """Return the final query string."""
        return self.base_query.strip()

    def declare_varchar(self, var_name: str, var_val: str) -> 'SQLQueryManager':
        if not re.fullmatch(r'[A-Za-z0-9_]+', var_name):
            raise ValueError(f'Invalid variable name: {var_name!r}')
        escaped_val = var_val.replace("'", "''")

        match = re.search(rf'DECLARE @{var_name.upper()} VARCHAR\((\d+)\)', self.base_query)
        if match:
            length = int(match.group(1))
            self.base_query = re.sub(
                rf"DECLARE @{var_name.upper()} VARCHAR\(\d+\) = '.*'",
                f"DECLARE @{var_name.upper()} VARCHAR({length}) = '{escaped_val}'",
                self.base_query,
            )
        else:
            self.base_query = (
                f"DECLARE @{var_name.upper()} VARCHAR(255) = '{escaped_val}'\n" + self.base_query
            )

        return self

    def declare_start_date(self, start_date: str) -> 'SQLQueryManager':
        """Declare a start date variable in format YYYY-MM-DD."""
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start_date):
            raise ValueError(f'Invalid date format: {start_date!r} — expected YYYY-MM-DD')
        if 'DECLARE @STARTDATE DATE =' in self.base_query:
            self.base_query = re.sub(
                r"DECLARE @STARTDATE DATE = '.*'",
                f"DECLARE @STARTDATE DATE = '{start_date}'",
                self.base_query,
            )
        else:
            raise ValueError('Query does not declare start date variable')
        return self

    def declare_end_date(self, end_date: str) -> 'SQLQueryManager':
        """Declare a end date variable in format YYYY-MM-DD."""
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', end_date):
            raise ValueError(f'Invalid date format: {end_date!r} — expected YYYY-MM-DD')
        if 'DECLARE @ENDDATE DATE =' in self.base_query:
            self.base_query = re.sub(
                r"DECLARE @ENDDATE DATE = (?:CAST\(GETDATE\(\) AS DATE\)|'.*')",
                f"DECLARE @ENDDATE DATE = '{end_date}'",
                self.base_query,
            )
        else:
            raise ValueError('Query does not declare end date variable')
        return self

    def insert_values_into_table(
        self, table_name: str, values: List[str | tuple[str]]
    ) -> 'SQLQueryManager':
        """Insert values into a table."""
        if f'DECLARE @{table_name.upper()} TABLE' not in self.base_query:
            raise ValueError(f'Query does not declare table variable @{table_name.upper()}')

        insert_pattern = re.compile(rf'INSERT INTO @{table_name.upper()} \((.*?)\)', re.IGNORECASE)
        match = insert_pattern.search(self.base_query)

        if not match:
            raise ValueError(
                f'Query does not contain an INSERT INTO clause for table @{table_name}'
            )

        real_field_keys = match.group(1).strip().split(',')

        val_check = (
            len(real_field_keys) == 1 and all(isinstance(value, str) for value in values)
        ) or all(
            isinstance(value, tuple) and len(value) == len(real_field_keys) for value in values
        )
        if not val_check:
            raise ValueError(f'{table_name.upper()} must contain {real_field_keys} values')

        if len(real_field_keys) == 1:
            value_strs = [f"('{value}')" for value in values]
        else:
            value_strs = [f'({", ".join(map(repr, value))})' for value in values]

        value_str = ','.join(value_strs)

        self.base_query = re.sub(
            rf'INSERT INTO @{table_name.upper()} \([^\)]+\) VALUES \([^\)]+\)(?:,\s*\([^\)]+\))*',
            f'INSERT INTO @{table_name.upper()} ({", ".join(real_field_keys)}) VALUES {value_str}',
            self.base_query,
        )

        return self

    # print(re.search(r"DECLARE @ENDDATE DATE = (?:CAST\(GETDATE\(\) AS DATE\)|'.*')", query_manager.base_query))
