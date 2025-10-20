from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import get_session
from models.event import Event
from models.event_seat import EventSeat
from models.ticket import Ticket


def purchase_event_seats(event_id: int, eventseat_ids: Iterable[int], customer_id: int) -> List[Tuple[Ticket, str]]:
	"""
	Attempt to sell the given EventSeat ids for an event and create tickets.
	Returns a list of (Ticket, seat_label) for successful purchases.
	Seats not available are skipped.
	"""
	now = datetime.now(tz=timezone.utc)
	created: List[Tuple[Ticket, str]] = []
	ids = [int(i) for i in eventseat_ids]
	if not ids:
		return created

	with get_session() as session:
		# Validate event exists (optional safety)
		_ = session.get(Event, event_id)

		# Load EventSeat rows with seat relationship
		rows = session.scalars(
			select(EventSeat)
			.where(EventSeat.event_id == event_id, EventSeat.id.in_(ids))
			.options(selectinload(EventSeat.seat))
		).all()

		id_to_es = {es.id: es for es in rows}

		# Process in requested order
		for esid in ids:
			es = id_to_es.get(esid)
			if not es or es.status not in ("AVAILABLE", "HELD"):
				continue
			# If HELD but expired, treat as AVAILABLE
			if es.status == "HELD" and es.held_until and es.held_until <= now:
				es.status = "AVAILABLE"
				es.held_until = None

			if es.status != "AVAILABLE":
				continue

			# Sell and create ticket
			es.status = "SOLD"
			es.held_until = None
			ticket = Ticket(
				customer_id=customer_id,
				event_seat_id=es.id,
				price_ksh=es.price_ksh,
				purchased_at=now,
			)
			session.add(ticket)
			# Compute seat label
			seat = es.seat if hasattr(es, "seat") else None
			label = f"{seat.row}{seat.number}" if seat else f"seat#{es.seat_id}"
			created.append((ticket, label))

	return created
