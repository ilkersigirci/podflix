"""SqlAlchemy database interface factory and implementations."""

from abc import ABC, abstractmethod
from pathlib import Path

from podflix.env_settings import env_settings


class SqlAlchemyDBInterface(ABC):
    """Abstract base class for database interfaces."""

    @abstractmethod
    def get_connection_path(self) -> str:
        """Returns the database connection path.

        Returns:
            A string representing the database connection path.
        """

    @abstractmethod
    def async_connection(self) -> str:
        """Returns the async database connection string.

        Returns:
            A string representing the async database connection URL.
        """

    @abstractmethod
    def sync_connection(self) -> str:
        """Returns the sync database connection string.

        Returns:
            A string representing the sync database connection URL.
        """

    def check_db_connection(self) -> None:
        """Checks if database connection is valid.

        Raises:
            Exception: If database connection fails, with details about the error.
        """
        from sqlalchemy import create_engine

        try:
            engine = create_engine(self.sync_connection())
            with engine.connect() as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            db_type = self.__class__.__name__.replace("DBInterface", "")
            raise Exception(f"{db_type} connection error:\n{e}") from e


class SQLiteDBInterface(SqlAlchemyDBInterface):
    """SQLite database interface implementation."""

    def __init__(self, db_path: str | Path = "db.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection_path(self) -> str:
        """Returns the SQLite database file path.

        Returns:
            A string representing the path to the SQLite database file.
        """
        return str(self.db_path)

    def async_connection(self) -> str:
        """Returns the async SQLite connection string.

        Returns:
            A string representing the async SQLite connection URL.
        """
        return f"sqlite+aiosqlite:///{self.get_connection_path()}"

    def sync_connection(self) -> str:
        """Returns the sync SQLite connection string.

        Returns:
            A string representing the sync SQLite connection URL.
        """
        return f"sqlite:///{self.get_connection_path()}"


class PostgresDBInterface(SqlAlchemyDBInterface):
    """PostgreSQL database interface implementation."""

    def get_connection_path(self) -> str:
        """Returns the PostgreSQL connection path.

        Returns:
            A string containing the PostgreSQL connection details including user, password, host, port and database.
        """
        return (
            f"{env_settings.postgres_user}:"
            f"{env_settings.postgres_password}@"
            f"{env_settings.postgres_host}:"
            f"{env_settings.postgres_port}/"
            f"{env_settings.postgres_db}"
        )

    def async_connection(self) -> str:
        """Returns the async PostgreSQL connection string.

        Returns:
            A string representing the async PostgreSQL connection URL.
        """
        return f"postgresql+asyncpg://{self.get_connection_path()}"

    def sync_connection(self) -> str:
        """Returns the sync PostgreSQL connection string.

        Returns:
            A string representing the sync PostgreSQL connection URL.
        """
        return f"postgresql://{self.get_connection_path()}"


class DBInterfaceFactory:
    """Singleton factory class for creating database interface instances."""

    _instance = None
    _db_interface = None

    def __new__(cls):  # noqa: D102
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def create(cls, db_path: str | Path = "db.sqlite") -> SqlAlchemyDBInterface:
        """Creates and returns appropriate database interface based on environment settings.

        Returns the same instance on subsequent calls.

        Args:
            db_path: Path to SQLite database file. Only used for SQLite interface.

        Returns:
            SqlAlchemyDBInterface: Singleton instance of appropriate database interface.
        """
        if cls._db_interface is None:
            if env_settings.sqlalchemy_db_type == "sqlite":
                cls._db_interface = SQLiteDBInterface(db_path)
            elif env_settings.sqlalchemy_db_type == "postgres":
                cls._db_interface = PostgresDBInterface()
            else:
                raise ValueError(
                    f"Invalid database type: {env_settings.sqlalchemy_db_type}. "
                    "Must be either 'sqlite' or 'postgres'"
                )
        return cls._db_interface
