from pathlib import Path

import sqlalchemy as sa
from loguru import logger

from podflix.db.db_factory import DBInterfaceFactory


def read_sql_file(file_path: str | Path) -> list[str]:
    with Path(file_path).open("r") as f:
        return [x.strip() for x in f.read().split(";") if x.strip()]


def initialize_db():
    logger.info("Initializing the database...")

    raw_sql_statements = read_sql_file(Path(__file__).parent / "init_db.sql")

    with sa.create_engine(
        DBInterfaceFactory.create().sync_connection()
    ).connect() as conn:
        for stmt in raw_sql_statements:
            conn.execute(sa.text(stmt))


if __name__ == "__main__":
    initialize_db()
