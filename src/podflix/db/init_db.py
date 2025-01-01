"""Initialize the database schema using SQL statements from init_db.sql file."""

import sqlite3
from pathlib import Path

import sqlalchemy as sa
from loguru import logger

from podflix.db.db_factory import DBInterfaceFactory


def read_sql_file(file_path: str | Path) -> list[str]:
    """Read and parse SQL statements from a file.

    Examples:
        >>> statements = read_sql_file("init_db.sql")
        >>> isinstance(statements, list)
        True

    Args:
        file_path: A string or Path object representing the path to the SQL file.

    Returns:
        A list of SQL statements as strings, with empty statements removed.
    """
    with Path(file_path).open("r") as f:
        return [x.strip() for x in f.read().split(";") if x.strip()]


def table_exists(conn) -> bool:
    """Check if any tables exist in the database.

    Args:
        conn: SQLAlchemy connection object

    Returns:
        bool: True if any tables exist, False otherwise
    """
    try:
        # Query to check for existing tables in the public schema
        query = """
            SELECT COUNT(*)
            FROM users
        """
        result = conn.execute(sa.text(query)).scalar()
        return result > 0
    except Exception as e:
        logger.error(f"Error checking for tables: {e}")
        return False


def initialize_db():
    """Initialize the database using SQL statements from init_db.sql file.

    The function only initializes the database if no tables exist.
    """
    engine = sa.create_engine(DBInterfaceFactory.create().sync_connection())

    with engine.connect() as conn:
        if table_exists(conn) is True:
            logger.info("Database already initialized, skipping...")
            return

        logger.info("Initializing the database...")
        raw_sql_statements = read_sql_file(Path(__file__).parent / "init_db.sql")
        for stmt in raw_sql_statements:
            conn.execute(sa.text(stmt))
        conn.commit()


if __name__ == "__main__":
    initialize_db()
