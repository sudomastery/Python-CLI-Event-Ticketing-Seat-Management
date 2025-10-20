from __future__ import annotations
from typing import Iterable, List
from sqlalchemy import select, func
from db import get_session
from models.seat import Seat

def ensure_seat_row(venue_id: int, row: str, numbers: Iterable[int]) -> int:
    created = 0
    nums = list(numbers)
    with get_session() as session:
        existing = set(session.scalars(
            select(Seat.number).where(Seat.venue_id == venue_id, Seat.row == row, Seat.number.in_(nums))
        ).all())
        to_create = [n for n in nums if n not in existing]
        if to_create:
            session.add_all([Seat(venue_id=venue_id, row=row, number=n) for n in to_create])
            created = len(to_create)
    return created

def ensure_grid(venue_id: int, rows: Iterable[str], numbers: Iterable[int]) -> int:
    total = 0
    for r in rows:
        total += ensure_seat_row(venue_id, r, numbers)
    return total

def list_seats_for_venue(venue_id: int) -> List[Seat]:
    with get_session() as session:
        return session.scalars(
            select(Seat).where(Seat.venue_id == venue_id).order_by(Seat.row, Seat.number)
        ).all()