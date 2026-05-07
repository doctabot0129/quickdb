from pathlib import Path


def read_query(sql_file_path: Path) -> str:
    with open(sql_file_path, 'r') as file:
        return file.read()


def resolve_project_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in (cur, *cur.parents):
        if (p / 'pyproject.toml').exists() or (p / '.git').exists():
            return p
    return cur
