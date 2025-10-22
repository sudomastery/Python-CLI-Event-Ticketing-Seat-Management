"""
Demo: list available seats, hold a few, sell one, release expired holds.

"""
from datetime import datetime, timezone
from sqlalchemy import select

# Ensure models are imported to register mappers
from models import Venue, Seat, Event, EventSeat  # noqa: F401

from db import get_session
from models.event import Event
from services.eventseat_service import (
    get_available_event_seats,
    hold_event_seats,
    sell_event_seat,
    release_expired_holds,
)

EVENT_NAME = "Opening Night"

def main() -> None:
    with get_session() as session:
        event = session.scalar(select(Event).where(Event.name == EVENT_NAME))
        if not event:
            print(f"Event '{EVENT_NAME}' not found. Run: python -m scripts.eventseat_smoke_test")
            return
        event_id = event.id

    avail = get_available_event_seats(event_id, limit=5)
    print("Available before hold:", [es.seat_id for es in avail])

    if not avail:
        print("Nothing to hold.")
        return

    to_hold = [es.seat_id for es in avail[:2]]
    held_ids = hold_event_seats(event_id, to_hold, minutes=10)
    print("Held EventSeat ids:", held_ids)

    if held_ids:
        ok = sell_event_seat(held_ids[0])
        print("Sell result:", ok)

    released = release_expired_holds(datetime.now(tz=timezone.utc))
    print("Expired holds released:", released)

    avail_after = get_available_event_seats(event_id, limit=5)
    print("Available after ops:", [es.seat_id for es in avail_after])

if __name__ == "__main__":
    main()