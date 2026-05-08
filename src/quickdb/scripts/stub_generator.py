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
