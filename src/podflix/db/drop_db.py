"""Drop all database tables using SQL statements from drop_db.sql file."""

from pathlib import Path

from podflix.db.db_manager import DatabaseManager


def drop_db(max_retries: int = 5, retry_delay: int = 2):
    """Drop all database tables using SQL statements from drop_db.sql file."""
    db_manager = DatabaseManager(max_retries, retry_delay)
    db_manager.execute_sql_file(
        Path(__file__).parent / "drop_db.sql",
        check_exists=False,
        operation_name="Dropping",
    )


if __name__ == "__main__":
    drop_db()
