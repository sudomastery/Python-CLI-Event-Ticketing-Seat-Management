"""
Seed a few seats for an existing venue, then query them back.

- Ensures the venue exists (creates it if missing).
- Inserts seats A1..A5 if none exist yet for that venue.
- Lists the seats.

Run from project root:
  python -m scripts.seat_smoke_test
"""
from sqlalchemy import select, func

from db import get_session
from models.venue import Venue
from models.seat import Seat


VENUE_NAME = "Nyayo National Stadium"

def main() -> None:
    # Ensure the venue exists; if not, create it
    with get_session() as session:
        venue = session.scalar(select(Venue).where(Venue.name == VENUE_NAME))
        if venue is None:
            venue = Venue(name=VENUE_NAME, address="Nairobi")
            session.add(venue)
            session.flush()  # get venue.id

        # If no seats yet for this venue, create A1..A5
        seat_count = session.scalar(
            select(func.count()).select_from(Seat).where(Seat.venue_id == venue.id)
        )
        if seat_count == 0:
            seats = [Seat(venue_id=venue.id, row="A", number=n) for n in range(1, 6)]
            session.add_all(seats)

    # Query back and print the seats
    with get_session() as session:
        rows = session.scalars(
            select(Seat)
            .where(Seat.venue_id == venue.id)
            .order_by(Seat.row, Seat.number)
        ).all()
        for s in rows:
            print(f"{VENUE_NAME}: {s.row}{s.number}")

if __name__ == "__main__":
    main()