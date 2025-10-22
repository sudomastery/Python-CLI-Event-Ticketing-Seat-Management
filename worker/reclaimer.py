"""
Reclaimer: clean up events that have already passed.

Behavior:
- Find events where start_at < now (UTC).
- Delete those events. Cascades will remove associated EventSeats and Tickets.

Run from project root:
  python -m worker.reclaimer

cronjob:

15 2 * * * cd /home/roy/dev/moringa/phase3/project/Python-CLI-Event-Ticketing-Seat-Management && DATABASE_URL='postgresql+psycopg://USER:PASS@localhost:5432/DBNAME' /home/roy/dev/moringa/phase3/project/Python-CLI-Event-Ticketing-Seat-Management/.venv/bin/python -m worker.reclaimer >> /home/roy/dev/moringa/phase3/project/reclaimer.log 2>&1
"""
from __future__ import annotations

from pathlib import Path
import sys
from datetime import datetime, timezone

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from db import get_session
from models.event import Event


def _fmt_event(e: Event) -> str:
	return f"{e.id}: {e.name} — {e.start_at.isoformat()}"


def list_events_by_expiry():
	now = datetime.now(tz=timezone.utc)
	with get_session() as session:
		healthy = session.scalars(select(Event).where(Event.start_at >= now).order_by(Event.start_at)).all()
		expired = session.scalars(select(Event).where(Event.start_at < now).order_by(Event.start_at)).all()
	return healthy, expired


def reclaim_past_events() -> list[tuple[int, str, str]]:
	"""Delete past events and return a list of removed (id, name, start_at_iso)."""
	now = datetime.now(tz=timezone.utc)
	removed: list[tuple[int, str, str]] = []
	with get_session() as session:
		past_events = session.scalars(select(Event).where(Event.start_at < now)).all()
		for e in past_events:
			removed.append((e.id, e.name, e.start_at.isoformat()))
			session.delete(e)
	return removed


def main() -> None:
	healthy, expired = list_events_by_expiry()
	print("Healthy (upcoming or ongoing) events:")
	if healthy:
		for e in healthy:
			print(" -", _fmt_event(e))
	else:
		print(" - None")

	print("\nExpired events (eligible for removal):")
	if expired:
		for e in expired:
			print(" -", _fmt_event(e))
	else:
		print(" - None")

	removed = reclaim_past_events()
	print("\nRemoved expired events:")
	if removed:
		for eid, name, when in removed:
			print(f" - {eid}: {name} — {when}")
	else:
		print(" - None")


if __name__ == "__main__":
	main()

