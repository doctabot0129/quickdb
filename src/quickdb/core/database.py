import logging
from typing import TYPE_CHECKING, List

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.automap import AutomapBase, automap_base

if TYPE_CHECKING:
    from quickdb.core.server import Server

logger = logging.getLogger(__name__)


class SQLDatabase:
    """Wraps a single database schema, backed by its own AutomapBase.

    Usage::

        db.prepare(autoload_with=engine, schema=db.database_name)
        row = session.query(db.classes.my_table).first()
    """

    def __init__(
        self, server: 'Server', database_name: str, full_init: bool = False
    ) -> None:
        self.server: 'Server' = server
        self.connection: sa.Connection = server.connection
        self.database_name: str = database_name
        # Each SQLDatabase owns its own AutomapBase so schemas don't collide.
        self._base: AutomapBase = automap_base()
        if full_init:
            self.prepare(autoload_with=self.server.engine, schema=self.database_name)

    # ------------------------------------------------------------------
    # AutomapBase delegation
    # ------------------------------------------------------------------

    def prepare(
        self,
        autoload_with: sa.Engine | None = None,
        schema: str | None = None,
        **kwargs,
    ) -> None:
        """Reflect the schema and map all tables.

        Delegates directly to the underlying ``AutomapBase.prepare()``, so any
        keyword arguments accepted by SQLAlchemy are passed through.
        """
        self._base.prepare(
            autoload_with=autoload_with or self.server.engine,
            schema=schema or self.database_name,
            **kwargs,
        )

    @property
    def tables(self) -> dict[str, sa.Table]:
        """Mapped table classes, e.g. ``db.tables.my_table``."""
        return self._base.classes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def load_table_list(self) -> List[str]:
        try:
            return sa.inspect(self.connection).get_table_names(schema=self.database_name)
        except SQLAlchemyError as e:
            logger.error('Failed to load table list for database %r: %s', self.database_name, e)
            raise
