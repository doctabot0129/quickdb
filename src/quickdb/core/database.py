import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING, List

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.automap import AutomapBase, automap_base

if TYPE_CHECKING:
    from quickdb.core.server import Server

logger = logging.getLogger(__name__)


class SQLDatabase:
    """Wraps a single database schema, backed by its own AutomapBase."""

    def __init__(
        self, server: 'Server', database_name: str, full_init: bool = False
    ) -> None:
        self.server: 'Server' = server
        self.connection: sa.Connection = server.connection
        self.database_name: str = database_name
        self._base: AutomapBase = automap_base()
        self._prepared: bool = False
        if full_init:
            self.prepare()

    def prepare(self, force_refresh: bool = False) -> None:
        """Reflect the schema and map tables, using pickle cache when available.

        Pass force_refresh=True to re-reflect and overwrite the cache.
        """
        cache_path = self._cache_path()
        if not force_refresh and cache_path.exists():
            with cache_path.open('rb') as f:
                metadata = pickle.load(f)
            self._base = automap_base(metadata=metadata)
            self._base.prepare()
        else:
            self._base.prepare(
                autoload_with=self.server.engine,
                schema=self.database_name,
            )
            cache_path.parent.mkdir(exist_ok=True)
            with cache_path.open('wb') as f:
                pickle.dump(self._base.metadata, f)
        self._prepared = True

    def _cache_path(self) -> Path:
        from quickdb.core.utils import resolve_project_root
        host = self.server.engine.url.host or 'local'
        return resolve_project_root() / '.quickdb_cache' / f'{host}_{self.database_name}.pkl'

    @property
    def tables(self):
        """Reflected table classes. Triggers prepare() on first access if not yet prepared."""
        if not self._prepared:
            self.prepare()
        return self._base.classes

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        if not self._prepared:
            self.prepare()
        try:
            return self._base.classes[name]
        except (KeyError, AttributeError):
            raise AttributeError(f"Table {name!r} not found in database {self.database_name!r}")

    def load_table_list(self) -> List[str]:
        try:
            return sa.inspect(self.connection).get_table_names(schema=self.database_name)
        except SQLAlchemyError as e:
            logger.error('Failed to load table list for database %r: %s', self.database_name, e)
            raise
