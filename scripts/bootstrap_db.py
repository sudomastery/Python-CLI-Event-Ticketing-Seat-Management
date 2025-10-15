"""
Bootstrap the database schema for local development.

- Imports models so SQLAlchemy registers their tables on Base.metadata.
- Calls create_all() to create any missing tables.
- Prints a DB healthcheck.

Tip: With SQL_ECHO=true in your .env, you’ll see the underlying SQL.
"""
from db import create_all, db_healthcheck

# Import your models so their tables are registered with Base.metadata
from models.venue import Venue  # noqa: F401  (import-only side effect)

def main() -> None:
    info = db_healthcheck()
    print(f"DB OK • version={info['server_version']} • now={info['now']}")
    create_all()
    print("Schema created (or already present).")

if __name__ == "__main__":
    main()