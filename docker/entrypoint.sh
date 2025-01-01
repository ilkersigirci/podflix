#!/bin/sh

uv run src/podflix/db/init_db.py

# Start the main application
exec "$@"
