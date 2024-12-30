"""Initialize the database schema using SQL statements from init_db.sql file."""

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


def initialize_db():
    """Initialize the database using SQL statements from init_db.sql file.

    Examples:
        >>> initialize_db()  # Creates/updates database schema

    The function reads SQL statements from the init_db.sql file in the same
    directory and executes them sequentially using a database connection.
    """
    logger.info("Initializing the database...")

    raw_sql_statements = read_sql_file(Path(__file__).parent / "init_db.sql")

    with sa.create_engine(
        DBInterfaceFactory.create().sync_connection()
    ).connect() as conn:
        for stmt in raw_sql_statements:
            conn.execute(sa.text(stmt))


if __name__ == "__main__":
    initialize_db()
