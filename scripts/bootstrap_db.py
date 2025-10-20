"""
Bootstrap the database schema for local development.

- Imports models so SQLAlchemy registers their tables on Base.metadata.
- Prints a DB healthcheck to confirm connectivity.
- Creates any missing tables (safe to re-run).
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import create_all, db_healthcheck

# Import models so their tables are registered with Base.metadata (import side effects)
from models.venue import Venue  # noqa: F401
from models.seat import Seat    # noqa: F401
from models.event import Event  # noqa: F401
from models.event_seat import EventSeat  # noqa: F401


def main() -> None:
    info = db_healthcheck()
    print(f"DB OK • version={info['server_version']} • now={info['now']}")
    create_all()
    print("Schema created (or already present).")


if __name__ == "__main__":
    main()