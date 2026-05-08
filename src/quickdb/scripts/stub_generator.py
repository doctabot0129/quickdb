from __future__ import annotations

import keyword
import re
from datetime import datetime
from pathlib import Path

from quickdb.core.database import SQLDatabase
from quickdb.core.server import Server
from quickdb.core.table import SQLTable


def _to_pascal_case(name: str) -> str:
    return ''.join(word.capitalize() for word in name.split('_'))


def _class_to_filename(class_name: str) -> str:
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', class_name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower() + '.pyi'


def _generate_table_stub(table_name: str, columns: list[str]) -> str:
    class_name = f'_{_to_pascal_case(table_name)}Table'
    safe_cols = [c for c in columns if c.isidentifier() and not keyword.iskeyword(c)]

    col_attrs = '\n'.join(f'    {col}: str' for col in safe_cols)

    if safe_cols:
        literal_fields = ', '.join(f"'{col}'" for col in safe_cols)
        fields_type = f'list[Literal[{literal_fields}]] | None'
    else:
        fields_type = 'list[str] | None'

    method = (
        f'    def limited_query(\n'
        f'        self,\n'
        f'        fields: {fields_type} = None,\n'
        f'        where: list[str] | None = None,\n'
        f'        limit: int = 10,\n'
        f'    ) -> pd.DataFrame: ...'
    )

    body = f'{col_attrs}\n\n{method}' if col_attrs else method
    return f'class {class_name}(SQLTable):\n{body}\n'


def _generate_database_stub(db_name: str, table_names: list[str]) -> str:
    class_name = f'_{_to_pascal_case(db_name)}Db'
    if table_names:
        body = '\n'.join(f'    {t}: _{_to_pascal_case(t)}Table' for t in table_names)
    else:
        body = '    pass'
    return f'class {class_name}(SQLDatabase):\n{body}\n'
