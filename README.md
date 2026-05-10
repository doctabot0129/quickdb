# quickdb

A lightweight Python wrapper for connecting to SQL databases. Provides server connection management, automatic schema reflection via SQLAlchemy's AutomapBase, and IDE autocomplete through generated `.pyi` stubs.

## Supported dialects

| Dialect | Convenience class | `db_type` string |
|---------|-------------------|------------------|
| SQL Server | `SQLServer` | `'mssql'` |
| MariaDB | `MariaDBServer` | `'mariadb'` |
| MySQL | `MySQLServer` | `'mysql'` |

Any dialect supported by SQLAlchemy can be added via the registry — see [Adding a new dialect](#adding-a-new-dialect).

## Installation

```bash
pip install quickdb
```

## Quick start

```python
import os
from dotenv import load_dotenv
from quickdb import MariaDBServer

load_dotenv()

with MariaDBServer(
    server_name='my-server',
    username=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
) as server:
    df = server.my_database.my_table.all.fetchall()
```

## Connecting to a server

Use a named subclass for the most common dialects:

```python
from quickdb import SQLServer, MariaDBServer, MySQLServer

server = SQLServer(server_name='sql-01', username='...', password='...')
server = MariaDBServer(server_name='mysql-01', username='...', password='...')
server = MySQLServer(server_name='mysql-02', username='...', password='...')
```

Or use `Server` directly with a `db_type` string:

```python
from quickdb import Server

server = Server(db_type='mariadb', server_name='mysql-01', username='...', password='...')
```

Always use the context manager to ensure the connection is closed cleanly:

```python
with MariaDBServer(server_name='...', username='...', password='...') as server:
    ...
```

## Accessing databases and tables

quickdb reflects your schema automatically using SQLAlchemy's AutomapBase. Databases and tables are accessed via attribute notation:

```python
# Access a database
db = server.my_database

# Access a table (triggers schema reflection on first access)
table = server.my_database.orders
```

### Controlling which databases are fully reflected

By default only the database passed in the connection string is fully reflected. Override `my_databases` on a subclass to control this:

```python
from quickdb import MariaDBServer

class MyServer(MariaDBServer):
    def __init__(self, **kwargs):
        super().__init__(server_name='my-server', **kwargs)

    @property
    def my_databases(self):
        return ['sales', 'inventory']
```

Databases listed in `my_databases` are fully reflected (and cached) at connection time. All other available databases are registered lazily and reflected on first access.

To eagerly reflect and cache all databases on the server, pass `cache_all=True`:

```python
with MyServer(cache_all=True) as server:
    ...
```

### Schema cache

Reflected metadata is cached as pickle files under `.quickdb_cache/` in your project root. This avoids re-reflecting on every run. To force a refresh:

```python
server.my_database.prepare(force_refresh=True)
```

## Generating IDE stubs

`StubGenerator` connects to a live server instance and writes a `.pyi` stub file next to the server's source file, giving IDEs full autocomplete across the `server → database → table → column` hierarchy.

```python
from dotenv import load_dotenv
from quickdb import StubGenerator
from mypackage.server import MyServer

load_dotenv()

with MyServer() as server:
    StubGenerator(server).generate()
```

The stub is written to `<server_module>.pyi` alongside the server's `.py` file. Run this script whenever your schema changes.

## Adding a new dialect

Add entries to both registries in `quickdb/core/server.py`:

```python
from quickdb.core.server import DRIVER_REGISTRY, DB_SELECT_REGISTRY

DRIVER_REGISTRY['postgres'] = 'postgresql+psycopg2'
DB_SELECT_REGISTRY['postgres'] = 'SELECT datname FROM pg_database'
```

Then connect with:

```python
server = Server(db_type='postgres', server_name='pg-01', username='...', password='...')
```

Or create a named subclass for convenience:

```python
from quickdb import Server

class PostgreSQLServer(Server):
    def __init__(self, server_name, **kwargs):
        super().__init__(db_type='postgres', server_name=server_name, **kwargs)
```

## SQLQueryManager

`SQLQueryManager` provides a fluent interface for modifying SQL queries loaded from `.sql` files.

```python
from quickdb import SQLQueryManager
from pathlib import Path

qm = (
    SQLQueryManager(Path('queries/orders.sql'))
    .change_db('production')
    .declare_start_date('2024-01-01')
    .declare_end_date('2024-12-31')
    .add_where_clause("status = 'complete'")
    .add_order_by(['order_date'])
)

df = server.query_mgr_to_pandas(qm)
```

Available methods:

| Method | Description |
|--------|-------------|
| `change_db(name)` | Replace the database name in the FROM clause |
| `add_where_clause(condition)` | Add a WHERE condition (creates clause or ANDs into existing) |
| `add_or_clause(condition)` | Add an OR condition to an existing WHERE clause |
| `add_group_by(columns)` | Add or extend a GROUP BY clause |
| `add_order_by(columns)` | Add or extend an ORDER BY clause |
| `declare_varchar(name, value)` | Set a VARCHAR variable declared in the query |
| `declare_start_date(date)` | Set `@STARTDATE` — format `YYYY-MM-DD` |
| `declare_end_date(date)` | Set `@ENDDATE` — format `YYYY-MM-DD` |
| `insert_values_into_table(name, values)` | Populate a table variable declared in the query |
| `get_query()` | Return the final query string |

## Environment variables

quickdb does not call `load_dotenv()` automatically. Load your `.env` file before constructing a server instance:

```python
from dotenv import load_dotenv
load_dotenv()
```
