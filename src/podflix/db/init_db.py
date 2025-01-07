"""Initialize the database schema using SQL statements from init_db.sql file."""

from pathlib import Path

from podflix.db.db_manager import DatabaseManager


def initialize_db(max_retries: int = 5, retry_delay: int = 2):
    """Initialize the database using SQL statements from init_db.sql file."""
    db_manager = DatabaseManager(max_retries, retry_delay)
    db_manager.execute_sql_file(
        Path(__file__).parent / "init_db.sql",
        check_exists=True,
        operation_name="Initializing",
    )


if __name__ == "__main__":
    initialize_db()
