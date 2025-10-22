"""
Seed EventSeat rows for an event and list availability.

"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func

from db import get_session
from models.venue import Venue
from models.seat import Seat
from models.event import Event
from models.event_seat import EventSeat

VENUE_NAME = "Nyayo National Stadium"
EVENT_NAME = "Opening Night"

def main() -> None:
    # Ensure venue + seats + event exist
    with get_session() as session:
        venue = session.scalar(select(Venue).where(Venue.name == VENUE_NAME))
        if venue is None:
            venue = Venue(name=VENUE_NAME, address="Nairobi")
            session.add(venue)
            session.flush()

        # Seed seats A1..A5 if none
        seat_count = session.scalar(select(func.count()).select_from(Seat).where(Seat.venue_id == venue.id))
        if seat_count == 0:
            session.add_all([Seat(venue_id=venue.id, row="A", number=n) for n in range(1, 6)])
            session.flush()

        event = session.scalar(select(Event).where(Event.venue_id == venue.id, Event.name == EVENT_NAME))
        if event is None:
            event = Event(
                venue_id=venue.id,
                name=EVENT_NAME,
                start_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
                description="Demo event",
            )
            session.add(event)
            session.flush()

        # Seed EventSeat rows if none for this event
        es_count = session.scalar(select(func.count()).select_from(EventSeat).where(EventSeat.event_id == event.id))
        if es_count == 0:
            seat_ids = session.scalars(select(Seat.id).where(Seat.venue_id == venue.id)).all()
            session.add_all([
                EventSeat(event_id=event.id, seat_id=sid, status="AVAILABLE", price_ksh=1500)
                for sid in seat_ids
            ])
        event_id = event.id

    # Show counts by status
    with get_session() as session:
        totals = session.execute(
            select(EventSeat.status, func.count()).where(EventSeat.event_id == event_id).group_by(EventSeat.status)
        ).all()
        print("EventSeat counts:", dict(totals))

        # Demonstrate a hold
        es = session.scalar(
            select(EventSeat).where(EventSeat.event_id == event_id, EventSeat.status == "AVAILABLE")
        )
        if es:
            es.status = "HELD"
            es.held_until = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
            print(f"Held seat_id={es.seat_id} until {es.held_until.isoformat()}")

    # Show updated counts
    with get_session() as session:
        totals = session.execute(
            select(EventSeat.status, func.count()).where(EventSeat.event_id == event_id).group_by(EventSeat.status)
        ).all()
        print("Updated counts:", dict(totals))

if __name__ == "__main__":
    main()