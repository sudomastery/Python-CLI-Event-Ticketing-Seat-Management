from __future__ import annotations
from typing import List, Optional
from sqlalchemy import select
from db import get_session
from models.venue import Venue


def get_or_create_venue(name: str, address: Optional[str] = None) -> Venue:
	with get_session() as session:
		v = session.scalar(select(Venue).where(Venue.name == name))
		if v:
			return v
		v = Venue(name=name, address=address)
		session.add(v)
		session.flush()
		return v


def list_venues() -> List[Venue]:
	with get_session() as session:
		return session.scalars(select(Venue).order_by(Venue.name)).all()

