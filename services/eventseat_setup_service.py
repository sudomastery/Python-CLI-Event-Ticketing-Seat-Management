from __future__ import annotations
from sqlalchemy import select
from db import get_session
from models.seat import Seat
from models.event_seat import EventSeat


def seed_event_seats(
    event_id: int,
    venue_id: int,
    price_ksh: int,
    only_missing: bool = True,
    seat_limit: int | None = None,
) -> int:
    """
    Create EventSeat rows for all seats in a venue for the given event.
    If only_missing, skip seats already present for this event.
    Returns number of EventSeat rows created.
    """
    created = 0
    with get_session() as session:
        # Deterministic ordering by row, number so capacity selection is predictable
        seat_ids = session.scalars(
            select(Seat.id).where(Seat.venue_id == venue_id).order_by(Seat.row, Seat.number)
        ).all()
        if seat_limit is not None and seat_limit >= 0:
            seat_ids = seat_ids[:seat_limit]
        if not seat_ids:
            return 0

        existing = set()
        if only_missing:
            existing = set(
                session.scalars(
                    select(EventSeat.seat_id).where(
                        EventSeat.event_id == event_id,
                        EventSeat.seat_id.in_(seat_ids),
                    )
                ).all()
            )

        to_add = [
            EventSeat(event_id=event_id, seat_id=sid, status="AVAILABLE", price_ksh=price_ksh)
            for sid in seat_ids
            if sid not in existing
        ]
        if to_add:
            session.add_all(to_add)
            created = len(to_add)
    return created