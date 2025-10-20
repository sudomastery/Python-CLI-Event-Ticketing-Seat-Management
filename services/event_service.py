from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from db import get_session
from models.event import Event

def get_or_create_event(venue_id: int, name: str, start_at: datetime, description: Optional[str] = None) -> Event:
    with get_session() as session:
        e = session.scalar(select(Event).where(Event.venue_id == venue_id, Event.name == name))
        if e:
            return e
        e = Event(venue_id=venue_id, name=name, start_at=start_at, description=description)
        session.add(e)
        session.flush()
        return e

def list_events_for_venue(venue_id: int) -> List[Event]:
    with get_session() as session:
        return session.scalars(
            select(Event).where(Event.venue_id == venue_id).order_by(Event.start_at)
        ).all()