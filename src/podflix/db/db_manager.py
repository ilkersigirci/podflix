"""Base database management functionality.

This module provides database management capabilities including initialization,
connection handling, and SQL file execution with retry logic.

Examples:
    >>> from podflix.db.db_manager import DatabaseManager
    >>> db_manager = DatabaseManager()
    >>> db_manager.execute_sql_file(Path("init.sql"), True, "Initialize")

The module contains the following class:

- `DatabaseManager` - Handles database operations with retry logic.
"""

from pathlib import Path

import sqlalchemy as sa
from loguru import logger
from sqlalchemy.exc import OperationalError, ProgrammingError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from podflix.db.db_factory import DBInterfaceFactory
from podflix.env_settings import env_settings


class DatabaseManager:
    """Manages database operations with retry logic and error handling.

    This class provides functionality to manage database operations including
    reading SQL files, checking table existence, and executing SQL statements
    with retry logic.

    Args:
        max_retries: Maximum number of connection retry attempts. Defaults to 5.
        retry_delay: Initial delay between retries in seconds. Defaults to 2.

    Examples:
        >>> db_manager = DatabaseManager(max_retries=3, retry_delay=1)
        >>> db_manager.execute_sql_file(Path("init.sql"), True, "Initialize")
    """

    def __init__(self, max_retries: int = 5, retry_delay: int = 2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.engine = sa.create_engine(DBInterfaceFactory.create().sync_connection())

    def read_sql_file(self, file_path: str | Path) -> list[str]:
        """Read and parse SQL statements from a file.

        Args:
            file_path: Path to the SQL file to be read.

        Returns:
            A list of SQL statements parsed from the file.

        Examples:
            >>> db_manager = DatabaseManager()
            >>> statements = db_manager.read_sql_file("init.sql")
            >>> len(statements) > 0
            True
        """
        with Path(file_path).open("r") as f:
            return [x.strip() for x in f.read().split(";") if x.strip()]

    def table_exists(self, conn) -> bool:
        """Check if users table exists in the database.

        Args:
            conn: SQLAlchemy connection object to use for the query.

        Returns:
            True if the users table exists, False otherwise.

        Raises:
            OperationalError: If there's a problem connecting to the database.
            ProgrammingError: If there's a problem executing the SQL query.

        Examples:
            >>> db_manager = DatabaseManager()
            >>> with db_manager.engine.connect() as conn:
            ...     exists = db_manager.table_exists(conn)
            >>> isinstance(exists, bool)
            True
        """
        try:
            if env_settings.sqlalchemy_db_type == "sqlite":
                query = """
                    SELECT COUNT(*)
                    FROM sqlite_master
                    WHERE type='table' AND name='users'
                """
            else:  # postgresql
                query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'users'
                    );
                """
            result = conn.execute(sa.text(query)).scalar()
            return bool(result)
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Error checking for tables: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(OperationalError),
        before_sleep=lambda retry_state: logger.warning(
            f"Database connection attempt {retry_state.attempt_number} failed, retrying..."
        ),
    )
    def execute_sql_file(self, sql_file: Path, check_exists: bool, operation_name: str):
        """Execute SQL statements from a file with retry logic.

        Args:
            sql_file: Path to the SQL file to execute.
            check_exists: If True, checks for existing tables before execution.
            operation_name: Name of the operation for logging purposes.

        Raises:
            OperationalError: If database connection fails after max retries.
            Exception: If SQL statement execution fails.

        Examples:
            >>> db_manager = DatabaseManager()
            >>> db_manager.execute_sql_file(
            ...     Path("init.sql"),
            ...     check_exists=True,
            ...     operation_name="Initialize"
            ... )
        """
        with self.engine.connect() as conn:
            exists = self.table_exists(conn)
            if check_exists and exists:
                logger.info("Database already initialized, skipping...")
                return

            if not check_exists and not exists:
                logger.info("No tables found in database, nothing to drop...")
                return

            logger.info(f"{operation_name} database...")
            raw_sql_statements = self.read_sql_file(sql_file)

            for stmt in raw_sql_statements:
                try:
                    conn.execute(sa.text(stmt))
                except Exception as e:
                    logger.error(f"Error executing statement: {e}")
                    raise

            conn.commit()
            logger.info(f"Database {operation_name.lower()} completed successfully")
