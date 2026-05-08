# Stub Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `StubGenerator` class to quickdb that introspects a live server's schema and writes a `.pyi` stub file for child server projects, giving IDEs full autocomplete for the `server.db.table` hierarchy and typed `fields` parameters on `limited_query`.

**Architecture:** Module-level private functions handle all stub text generation (table classes, database classes, server class, file header). `StubGenerator` orchestrates these: it walks `server.my_databases` to introspect schema via live DB queries, builds the full stub content, and writes one `.pyi` file. Databases in `all_databases_list` but not `my_databases` get surface-tier stubs typed as `SQLDatabase` with a discoverability comment.

**Tech Stack:** Python 3.14, SQLAlchemy 2.x, pytest, `re` (stdlib), `keyword` (stdlib), `pathlib` (stdlib)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/quickdb/scripts/__init__.py` | Create | Makes `scripts` a package |
| `src/quickdb/scripts/stub_generator.py` | Create | All helper functions + `StubGenerator` class |
| `src/quickdb/__init__.py` | Modify | Export `StubGenerator` |
| `tests/__init__.py` | Create | Makes `tests` a package |
| `tests/test_stub_generator.py` | Create | All tests |

---

## Task 1: Project structure and naming utilities

**Files:**
- Create: `src/quickdb/scripts/__init__.py`
- Create: `src/quickdb/scripts/stub_generator.py`
- Create: `tests/__init__.py`
- Create: `tests/test_stub_generator.py`

- [ ] **Step 1: Create package inits**

Create `src/quickdb/scripts/__init__.py` — empty file.

Create `tests/__init__.py` — empty file.

- [ ] **Step 2: Create `stub_generator.py` with naming helpers**

Create `src/quickdb/scripts/stub_generator.py`:

```python
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
```

- [ ] **Step 3: Write tests for naming helpers**

Create `tests/test_stub_generator.py`:

```python
from quickdb.scripts.stub_generator import _to_pascal_case, _class_to_filename


def test_to_pascal_case_single_word():
    assert _to_pascal_case('cases') == 'Cases'


def test_to_pascal_case_snake_case():
    assert _to_pascal_case('case_updates') == 'CaseUpdates'


def test_to_pascal_case_single_segment():
    assert _to_pascal_case('suitecrm') == 'Suitecrm'


def test_to_pascal_case_multi_segment():
    assert _to_pascal_case('my_warehouse') == 'MyWarehouse'


def test_class_to_filename_sqlserver():
    assert _class_to_filename('SQLServer') == 'sql_server.pyi'


def test_class_to_filename_suitecrm():
    assert _class_to_filename('SuiteCRMServer') == 'suite_crm_server.pyi'


def test_class_to_filename_mariadb():
    assert _class_to_filename('MariaDBServer') == 'maria_db_server.pyi'


def test_class_to_filename_simple():
    assert _class_to_filename('MyServer') == 'my_server.pyi'
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_stub_generator.py -v
```

Expected: all 8 pass.

- [ ] **Step 5: Commit**

```bash
git add src/quickdb/scripts/__init__.py src/quickdb/scripts/stub_generator.py tests/__init__.py tests/test_stub_generator.py
git commit -m "feat: add scripts package and naming utilities for stub generator"
```

---

## Task 2: Table stub generation

**Files:**
- Modify: `src/quickdb/scripts/stub_generator.py`
- Modify: `tests/test_stub_generator.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_stub_generator.py`:

```python
from quickdb.scripts.stub_generator import _generate_table_stub


def test_table_stub_class_name():
    result = _generate_table_stub('cases', ['id', 'name'])
    assert 'class _CasesTable(SQLTable):' in result


def test_table_stub_snake_case_name():
    result = _generate_table_stub('case_updates', ['id'])
    assert 'class _CaseUpdatesTable(SQLTable):' in result


def test_table_stub_column_attrs():
    result = _generate_table_stub('cases', ['id', 'name', 'entered_date'])
    assert '    id: str' in result
    assert '    name: str' in result
    assert '    entered_date: str' in result


def test_table_stub_literal_fields_in_limited_query():
    result = _generate_table_stub('cases', ['id', 'name'])
    assert "Literal['id', 'name']" in result
    assert '-> pd.DataFrame: ...' in result


def test_table_stub_skips_python_keywords():
    result = _generate_table_stub('orders', ['id', 'from', 'return'])
    assert '    id: str' in result
    assert '    from: str' not in result
    assert '    return: str' not in result


def test_table_stub_skips_non_identifiers():
    result = _generate_table_stub('orders', ['id', '1bad', 'has space'])
    assert '    id: str' in result
    assert '    1bad: str' not in result
    assert '    has space: str' not in result


def test_table_stub_no_valid_columns_uses_generic_fields_type():
    result = _generate_table_stub('orders', ['from', 'return'])
    assert 'list[str] | None' in result
    assert 'Literal' not in result
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_stub_generator.py::test_table_stub_class_name -v
```

Expected: `ImportError` — `_generate_table_stub` not yet defined.

- [ ] **Step 3: Implement `_generate_table_stub`**

Add to `src/quickdb/scripts/stub_generator.py`:

```python
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
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_stub_generator.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quickdb/scripts/stub_generator.py tests/test_stub_generator.py
git commit -m "feat: add table stub generation with Literal field types"
```

---

## Task 3: Database stub generation

**Files:**
- Modify: `src/quickdb/scripts/stub_generator.py`
- Modify: `tests/test_stub_generator.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_stub_generator.py`:

```python
from quickdb.scripts.stub_generator import _generate_database_stub


def test_database_stub_class_name():
    result = _generate_database_stub('suitecrm', ['cases', 'accounts'])
    assert 'class _SuitecrmDb(SQLDatabase):' in result


def test_database_stub_snake_case_name():
    result = _generate_database_stub('my_warehouse', ['orders'])
    assert 'class _MyWarehouseDb(SQLDatabase):' in result


def test_database_stub_table_attrs():
    result = _generate_database_stub('suitecrm', ['cases', 'accounts'])
    assert '    cases: _CasesTable' in result
    assert '    accounts: _AccountsTable' in result


def test_database_stub_no_tables_emits_pass():
    result = _generate_database_stub('empty_db', [])
    assert 'class _EmptyDbDb(SQLDatabase):' in result
    assert '    pass' in result
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_stub_generator.py::test_database_stub_class_name -v
```

Expected: `ImportError` — `_generate_database_stub` not defined.

- [ ] **Step 3: Implement `_generate_database_stub`**

Add to `src/quickdb/scripts/stub_generator.py`:

```python
def _generate_database_stub(db_name: str, table_names: list[str]) -> str:
    class_name = f'_{_to_pascal_case(db_name)}Db'
    if table_names:
        body = '\n'.join(f'    {t}: _{_to_pascal_case(t)}Table' for t in table_names)
    else:
        body = '    pass'
    return f'class {class_name}(SQLDatabase):\n{body}\n'
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_stub_generator.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quickdb/scripts/stub_generator.py tests/test_stub_generator.py
git commit -m "feat: add database stub generation"
```

---

## Task 4: File header and server class stub generation

**Files:**
- Modify: `src/quickdb/scripts/stub_generator.py`
- Modify: `tests/test_stub_generator.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_stub_generator.py`:

```python
from quickdb.scripts.stub_generator import _generate_file_header, _generate_server_stub


def test_file_header_contains_banner():
    result = _generate_file_header('quickdb.core.server', 'MariaDBServer')
    assert '# AUTO-GENERATED by quickdb StubGenerator' in result
    assert 'do not edit by hand' in result


def test_file_header_imports():
    result = _generate_file_header('quickdb.core.server', 'MariaDBServer')
    assert 'import pandas as pd' in result
    assert 'from typing import Literal' in result
    assert 'from quickdb import SQLDatabase, SQLTable' in result
    assert 'from quickdb.core.server import MariaDBServer' in result


def test_file_header_uses_correct_parent_module():
    result = _generate_file_header('mypackage.servers', 'PostgreSQLServer')
    assert 'from mypackage.servers import PostgreSQLServer' in result


def test_server_stub_class_definition():
    result = _generate_server_stub('SuiteCRMServer', 'MariaDBServer', ['suitecrm'], ['mysql'])
    assert 'class SuiteCRMServer(MariaDBServer):' in result


def test_server_stub_deep_db_attribute():
    result = _generate_server_stub('SuiteCRMServer', 'MariaDBServer', ['suitecrm'], [])
    assert '    suitecrm: _SuitecrmDb' in result


def test_server_stub_surface_db_attribute():
    result = _generate_server_stub('SuiteCRMServer', 'MariaDBServer', [], ['information_schema'])
    assert '    information_schema: SQLDatabase' in result
    assert 'add to my_databases for full stubs' in result


def test_server_stub_deep_and_surface_sections():
    result = _generate_server_stub(
        'SuiteCRMServer', 'MariaDBServer', ['suitecrm'], ['information_schema', 'mysql']
    )
    assert '    suitecrm: _SuitecrmDb' in result
    assert '    information_schema: SQLDatabase' in result
    assert '    mysql: SQLDatabase' in result


def test_server_stub_empty_emits_pass():
    result = _generate_server_stub('MyServer', 'SQLServer', [], [])
    assert '    pass' in result
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_stub_generator.py::test_file_header_contains_banner -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `_generate_file_header` and `_generate_server_stub`**

Add to `src/quickdb/scripts/stub_generator.py`:

```python
def _generate_file_header(parent_module: str, parent_class_name: str) -> str:
    timestamp = datetime.now().isoformat(timespec='seconds')
    return (
        f'# AUTO-GENERATED by quickdb StubGenerator — do not edit by hand\n'
        f'# Generated: {timestamp}\n'
        f'\n'
        f'import pandas as pd\n'
        f'from typing import Literal\n'
        f'from quickdb import SQLDatabase, SQLTable\n'
        f'from {parent_module} import {parent_class_name}\n'
    )


def _generate_server_stub(
    server_class_name: str,
    parent_class_name: str,
    deep_db_names: list[str],
    surface_db_names: list[str],
) -> str:
    lines = [f'class {server_class_name}({parent_class_name}):']

    if deep_db_names:
        lines.append('    # fully stubbed')
        for db_name in deep_db_names:
            lines.append(f'    {db_name}: _{_to_pascal_case(db_name)}Db')

    if surface_db_names:
        lines.append('    # available — add to my_databases for full stubs')
        for db_name in surface_db_names:
            lines.append(f'    {db_name}: SQLDatabase')

    if not deep_db_names and not surface_db_names:
        lines.append('    pass')

    return '\n'.join(lines) + '\n'
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_stub_generator.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quickdb/scripts/stub_generator.py tests/test_stub_generator.py
git commit -m "feat: add file header and server stub generation"
```

---

## Task 5: StubGenerator class

**Files:**
- Modify: `src/quickdb/scripts/stub_generator.py`
- Modify: `tests/test_stub_generator.py`

- [ ] **Step 1: Write failing integration tests**

Add to `tests/test_stub_generator.py`:

```python
import tempfile
from unittest.mock import MagicMock, patch

from quickdb.core.server import MariaDBServer
from quickdb.scripts.stub_generator import StubGenerator


class SuiteCRMServer(MariaDBServer):
    """Test double — represents a child server subclass."""


def _make_test_server() -> SuiteCRMServer:
    inst = object.__new__(SuiteCRMServer)
    inst.my_databases = ['suitecrm']
    inst.all_databases_list = ['suitecrm', 'information_schema', 'mysql']
    inst.connection = MagicMock()
    return inst


def test_stub_generator_writes_pyi_file():
    server = _make_test_server()
    with (
        patch('quickdb.scripts.stub_generator.SQLDatabase') as MockDb,
        patch('quickdb.scripts.stub_generator.SQLTable') as MockTable,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        MockDb.return_value.all_tables_list = ['cases']
        MockTable.return_value.all_columns_list = ['id', 'name']

        output = StubGenerator(server, output_path=tmpdir).generate()

        assert output.exists()
        assert output.suffix == '.pyi'
        assert output.name == 'suite_crm_server.pyi'


def test_stub_generator_deep_db_in_output():
    server = _make_test_server()
    with (
        patch('quickdb.scripts.stub_generator.SQLDatabase') as MockDb,
        patch('quickdb.scripts.stub_generator.SQLTable') as MockTable,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        MockDb.return_value.all_tables_list = ['cases']
        MockTable.return_value.all_columns_list = ['id', 'name']

        output = StubGenerator(server, output_path=tmpdir).generate()
        content = output.read_text()

        assert 'class _CasesTable(SQLTable):' in content
        assert 'class _SuitecrmDb(SQLDatabase):' in content
        assert '    suitecrm: _SuitecrmDb' in content
        assert "Literal['id', 'name']" in content


def test_stub_generator_surface_dbs_in_output():
    server = _make_test_server()
    with (
        patch('quickdb.scripts.stub_generator.SQLDatabase') as MockDb,
        patch('quickdb.scripts.stub_generator.SQLTable') as MockTable,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        MockDb.return_value.all_tables_list = ['cases']
        MockTable.return_value.all_columns_list = ['id']

        output = StubGenerator(server, output_path=tmpdir).generate()
        content = output.read_text()

        assert '    information_schema: SQLDatabase' in content
        assert '    mysql: SQLDatabase' in content
        assert 'add to my_databases for full stubs' in content


def test_stub_generator_correct_parent_import():
    server = _make_test_server()
    with (
        patch('quickdb.scripts.stub_generator.SQLDatabase') as MockDb,
        patch('quickdb.scripts.stub_generator.SQLTable') as MockTable,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        MockDb.return_value.all_tables_list = []
        MockTable.return_value.all_columns_list = []

        output = StubGenerator(server, output_path=tmpdir).generate()
        content = output.read_text()

        assert 'from quickdb.core.server import MariaDBServer' in content
        assert 'class SuiteCRMServer(MariaDBServer):' in content


def test_stub_generator_returns_path_to_written_file():
    server = _make_test_server()
    with (
        patch('quickdb.scripts.stub_generator.SQLDatabase') as MockDb,
        patch('quickdb.scripts.stub_generator.SQLTable') as MockTable,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        MockDb.return_value.all_tables_list = []
        MockTable.return_value.all_columns_list = []

        result = StubGenerator(server, output_path=tmpdir).generate()

        assert result.is_absolute()
        assert result.exists()
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_stub_generator.py::test_stub_generator_writes_pyi_file -v
```

Expected: `ImportError` — `StubGenerator` not defined.

- [ ] **Step 3: Implement `StubGenerator`**

Add to `src/quickdb/scripts/stub_generator.py`:

```python
class StubGenerator:
    def __init__(self, server: Server, output_path: str | Path) -> None:
        self.server = server
        self.output_path = Path(output_path)

    def generate(self) -> Path:
        deep_schema: dict[str, dict[str, list[str]]] = {}
        for db_name in self.server.my_databases:
            db = SQLDatabase(self.server.connection, db_name)
            deep_schema[db_name] = {
                table_name: SQLTable(self.server.connection, db_name, table_name).all_columns_list
                for table_name in db.all_tables_list
            }

        surface_dbs = [
            db for db in self.server.all_databases_list
            if db not in self.server.my_databases
        ]

        parent_cls = type(self.server).__bases__[0]
        server_class_name = type(self.server).__name__

        content = self._build_content(
            server_class_name=server_class_name,
            parent_class_name=parent_cls.__name__,
            parent_module=parent_cls.__module__,
            deep_schema=deep_schema,
            surface_dbs=surface_dbs,
        )

        output_file = self.output_path / _class_to_filename(server_class_name)
        output_file.write_text(content, encoding='utf-8')
        return output_file

    def _build_content(
        self,
        server_class_name: str,
        parent_class_name: str,
        parent_module: str,
        deep_schema: dict[str, dict[str, list[str]]],
        surface_dbs: list[str],
    ) -> str:
        sep = '─' * 50
        parts: list[str] = [_generate_file_header(parent_module, parent_class_name)]

        if deep_schema:
            parts += [f'# ── Deep stubs (my_databases) {sep}', '']
            for db_name, tables in deep_schema.items():
                for table_name, columns in tables.items():
                    parts += [_generate_table_stub(table_name, columns), '']
                parts += [_generate_database_stub(db_name, list(tables.keys())), '']

        parts += [f'# ── Server {sep}', '']
        parts.append(_generate_server_stub(
            server_class_name=server_class_name,
            parent_class_name=parent_class_name,
            deep_db_names=list(deep_schema.keys()),
            surface_db_names=surface_dbs,
        ))

        return '\n'.join(parts)
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_stub_generator.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quickdb/scripts/stub_generator.py tests/test_stub_generator.py
git commit -m "feat: implement StubGenerator class with two-tier schema introspection"
```

---

## Task 6: Export from quickdb public API

**Files:**
- Modify: `src/quickdb/__init__.py`
- Modify: `tests/test_stub_generator.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_stub_generator.py`:

```python
def test_stub_generator_importable_from_quickdb():
    from quickdb import StubGenerator  # noqa: F401
    assert StubGenerator is not None
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_stub_generator.py::test_stub_generator_importable_from_quickdb -v
```

Expected: `ImportError`.

- [ ] **Step 3: Add export to `__init__.py`**

In `src/quickdb/__init__.py`, add the import and update `__all__`:

```python
from quickdb.scripts.stub_generator import StubGenerator

__all__ = [
    'SQLDatabase',
    'SQLTable',
    'MariaDBServer',
    'SQLServer',
    'SQLQueryManager',
    'StubGenerator',
    'read_query',
    'resolve_project_root',
]
```

- [ ] **Step 4: Run full test suite**

```
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quickdb/__init__.py tests/test_stub_generator.py
git commit -m "feat: export StubGenerator from quickdb public API"
```
