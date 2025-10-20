from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import get_session
from models.event_seat import EventSeat


def get_available_event_seats(event_id: int, limit: int = 10) -> List[EventSeat]:
    with get_session() as session:
        return session.scalars(
            select(EventSeat)
            .where(EventSeat.event_id == event_id, EventSeat.status == "AVAILABLE")
            .order_by(EventSeat.seat_id)
            .limit(limit)
        ).all()


def hold_event_seats(event_id: int, seat_ids: Iterable[int], minutes: int = 15) -> List[int]:
    """Hold specific seats if they are currently AVAILABLE."""
    if minutes <= 0:
        minutes = 15
    hold_until = datetime.now(tz=timezone.utc) + timedelta(minutes=minutes)

    held_ids: List[int] = []
    with get_session() as session:
        rows = session.scalars(
            select(EventSeat)
            .where(
                EventSeat.event_id == event_id,
                EventSeat.seat_id.in_(list(seat_ids)),
                EventSeat.status == "AVAILABLE",
            )
            .with_for_update(skip_locked=True)
        ).all()

        for es in rows:
            es.status = "HELD"
            es.held_until = hold_until
            held_ids.append(es.id)

    return held_ids


def sell_event_seat(eventseat_id: int) -> bool:
    """Mark a seat SOLD if AVAILABLE or HELD (and not expired)."""
    now = datetime.now(tz=timezone.utc)
    with get_session() as session:
        es = session.get(EventSeat, eventseat_id, with_for_update=True)
        if es is None:
            return False

        if es.status == "AVAILABLE":
            es.status = "SOLD"
            es.held_until = None
            return True

        if es.status == "HELD" and es.held_until and es.held_until > now:
            es.status = "SOLD"
            es.held_until = None
            return True

        return False


def release_expired_holds(now: Optional[datetime] = None) -> int:
    """Set status back to AVAILABLE where HELD and held_until <= now."""
    if now is None:
        now = datetime.now(tz=timezone.utc)

    with get_session() as session:
        result = session.execute(
            update(EventSeat)
            .where(
                EventSeat.status == "HELD",
                EventSeat.held_until.is_not(None),
                EventSeat.held_until <= now,
            )
            .values(status="AVAILABLE", held_until=None)
        )
        return result.rowcount or 0