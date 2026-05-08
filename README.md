# quickdb

A lightweight Python foundation for connecting to SQL databases and running queries. Provides server connection management, database/table introspection, and a fluent SQL query builder.

## Supported dialects

| Dialect | Class |
|---------|-------|
| SQL Server | `SQLServer` |
| MariaDB / MySQL | `MariaDBServer` |

## Installation

```bash
pip install quickdb
```

## Usage

### Connecting to a server

Use the server as a context manager to ensure the connection is always closed cleanly.

```python
import os
from dotenv import load_dotenv
from quickdb import SQLServer, MariaDBServer

load_dotenv()

with SQLServer(
    server_name='my-server',
    username=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
) as server:
    ...
```

### Loading databases and tables

```python
with SQLServer(server_name='my-server', username='...', password='...') as server:
    # Inspect available databases
    print(server.all_databases_list)

    # Load a single database
    server.load_database('my_database')

    # Load a table from that database
    server.my_database.load_table('orders')

    # Inspect available columns
    print(server.my_database.orders.all_columns_list)
```

### Running a quick query

`limited_query` returns a Pandas DataFrame and accepts optional field selection and WHERE conditions.

```python
df = server.my_database.orders.limited_query(
    fields=['order_id', 'customer_id', 'order_date'],
    where=["status = 'active'"],
    limit=100,
)
```

### SQLQueryManager

`SQLQueryManager` provides a fluent interface for building and modifying SQL queries loaded from `.sql` files.

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

### Subclassing Server

To add a new dialect, subclass `Server` and implement `driver_name` and `load_database_list`.

```python
from quickdb.core.server import Server
import sqlalchemy as sa

class PostgreSQLServer(Server):
    @property
    def driver_name(self) -> str:
        return 'postgresql+psycopg2'

    def load_database_list(self) -> list[str]:
        result = self.connection.execute(sa.text('SELECT datname FROM pg_database'))
        return [row[0] for row in result.fetchall()]
```

## Environment variables

quickdb does not call `load_dotenv()` automatically. Load your `.env` file in your script before constructing a server instance.

```python
from dotenv import load_dotenv
load_dotenv()
```
