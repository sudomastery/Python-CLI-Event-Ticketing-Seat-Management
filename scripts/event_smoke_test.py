"""
Create one event for an existing venue and list events.
Run from project root:
  python -m scripts.event_smoke_test
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from datetime import datetime, timezone
from sqlalchemy import select

from db import get_session
from models.venue import Venue
from models.event import Event
from models.seat import Seat          # noqa: F401  ensure model is registered
from models.event_seat import EventSeat  # noqa: F401  optional, but safe


VENUE_NAME = "Nyayo National Stadium"
EVENT_NAME = "Opening Night"

def main() -> None:
    # Ensure venue exists and capture id for reuse outside the session
    with get_session() as session:
        venue = session.scalar(select(Venue).where(Venue.name == VENUE_NAME))
        if venue is None:
            venue = Venue(name=VENUE_NAME, address="Nairobi")
            session.add(venue)
            session.flush()  # get venue.id
        venue_id = venue.id

        # Create an event if none exists for this venue/name
        existing = session.scalar(
            select(Event).where(Event.venue_id == venue_id, Event.name == EVENT_NAME)
        )
        if existing is None:
            show = Event(
                venue_id=venue_id,
                name=EVENT_NAME,
                start_at=datetime.now(tz=timezone.utc),
                description="Demo opening night",
            )
            session.add(show)

    # List events
    with get_session() as session:
        events = session.scalars(
            select(Event).where(Event.venue_id == venue_id).order_by(Event.start_at)
        ).all()
        for e in events:
            print(f"{VENUE_NAME} • {e.name} • {e.start_at.isoformat()}")

if __name__ == "__main__":
    main()