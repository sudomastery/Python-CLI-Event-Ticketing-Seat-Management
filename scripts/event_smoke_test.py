"""
Create one event for an existing venue and list events.
Run from project root:
  python -m scripts.event_smoke_test
"""
from datetime import datetime, timezone
from sqlalchemy import select

from db import get_session
from models.venue import Venue
from models.event import Event

VENUE_NAME = "Nyayo National Stadium"

def main() -> None:
    # Ensure venue exists
    with get_session() as session:
        venue = session.scalar(select(Venue).where(Venue.name == VENUE_NAME))
        if venue is None:
            venue = Venue(name=VENUE_NAME, address="Nairobi")
            session.add(venue)
            session.flush()  # get venue.id

        # Create an event if none exists for this venue
        existing = session.scalar(select(Event).where(Event.venue_id == venue.id))
        if existing is None:
            show = Event(
                venue_id=venue.id,
                name="Opening Night Performance by Sauti Sol",
                start_at=datetime.now(tz=timezone.utc),
                description="Main performance by Sauti Sol"
            )
            session.add(show)

    # List events
    with get_session() as session:
        events = session.scalars(
            select(Event).where(Event.venue_id == venue.id).order_by(Event.start_at)
        ).all()
        for e in events:
            print(f"{VENUE_NAME} • {e.name} • {e.start_at.isoformat()}")

if __name__ == "__main__":
    main()