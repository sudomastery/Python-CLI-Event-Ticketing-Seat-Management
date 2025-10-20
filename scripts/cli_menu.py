from __future__ import annotations

"""
Text-menu CLI with Admin and Customer workflows.

Run:
  python -m scripts.cli_menu
"""
import sys
from pathlib import Path
import math
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
import logging

# Hard-disable all logging noise for this interactive CLI
logging.disable(logging.CRITICAL)

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _quiet_sqlalchemy_logs() -> None:
    names = [
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.pool",
        "sqlalchemy.orm",
        "sqlalchemy.dialects",
    ]
    for n in names:
        lg = logging.getLogger(n)
    lg.setLevel(logging.CRITICAL)
    lg.propagate = False
    lg.disabled = True
    # replace handlers with a NullHandler to be extra safe
    lg.handlers = [logging.NullHandler()]

_quiet_sqlalchemy_logs()

# Register all model mappers
import models  # noqa: F401

from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from db import get_session
from models.venue import Venue
from models.event import Event
from models.event_seat import EventSeat
from models.seat import Seat

from services.venue_services import get_or_create_venue
from services.event_service import (
    get_or_create_event,
    list_all_events,
    delete_event,
)
from services.eventseat_setup_service import seed_event_seats
from services.eventseat_service import sell_event_seat
from services.seat_service import ensure_grid


def input_nonempty(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s


def pause() -> None:
    input("\nPress Enter to continue...")


# ---------- Admin workflow ----------

def admin_create_event() -> None:
    venue_name = input_nonempty("Venue name: ")
    with get_session() as session:
        venue = session.scalar(select(Venue).where(Venue.name == venue_name))
    if not venue:
        print("Venue not found. Creating it...")
        address = input("Venue address: ").strip() or None
        venue = get_or_create_venue(venue_name, address=address)

    name = input_nonempty("Event name: ")
    in_days_str = input("Starts in how many days? [7]: ").strip() or "7"
    try:
        in_days = int(in_days_str)
    except ValueError:
        in_days = 7
    desc = input("Description (optional): ").strip() or None

    start_at = datetime.now(tz=timezone.utc) + timedelta(days=in_days)
    event = get_or_create_event(venue.id, name, start_at, desc)
    print(f"Created/Found Event {event.id}: {event.name} @ {event.start_at.isoformat()}")

    # Capacity (default 50) and grid arrangement
    cap_input = input("Number of seats for this event [50]: ").strip() or "50"
    try:
        capacity = max(1, int(cap_input))
    except ValueError:
        capacity = 50

    # Simple grid: 10 seats per row; compute rows needed for capacity
    seats_per_row = 10
    rows_count = max(1, math.ceil(capacity / seats_per_row))
    rows = [chr(ord('A') + i) for i in range(rows_count)]
    numbers = list(range(1, seats_per_row + 1))

    # Ensure venue has at least this grid
    created_seats = ensure_grid(venue.id, rows, numbers)
    if created_seats:
        print(f"Created {created_seats} venue seats to match capacity.")

    # Price (default 1500) and auto-seed EventSeat rows limited by capacity
    price_str = input("Price KSh (e.g., 1500) [1500]: ").strip() or "1500"
    try:
        price = int(price_str)
    except ValueError:
        price = 1500
    created = seed_event_seats(event.id, venue.id, price, only_missing=True, seat_limit=capacity)
    print(f"Seeded {created} EventSeat rows.")


def admin_list_events() -> None:
    with get_session() as session:
        rows = session.scalars(
            select(Event).options(selectinload(Event.venue)).order_by(Event.start_at)
        ).all()
        # Aggregate EventSeat counts per event for visibility
        if rows:
            event_ids = [e.id for e in rows]
            counts = session.execute(
                select(
                    EventSeat.event_id,
                    func.count().label("total"),
                    func.sum(case((EventSeat.status == "AVAILABLE", 1), else_=0)).label("avail"),
                )
                .where(EventSeat.event_id.in_(event_ids))
                .group_by(EventSeat.event_id)
            ).all()
            count_map = {eid: (avail or 0, total or 0) for eid, total, avail in counts}
        else:
            count_map = {}
    if not rows:
        print("No events.")
        return
    for e in rows:
        vname = e.venue.name if e.venue else "?"
        avail, total = count_map.get(e.id, (0, 0))
        suffix = f" [seats: {avail}/{total} available]" if total else ""
        print(f"{e.id}: {e.name} — {vname} — {e.start_at.isoformat()}{suffix}")


def admin_delete_event() -> None:
    eid_str = input_nonempty("Event ID to delete: ")
    try:
        eid = int(eid_str)
    except ValueError:
        print("Invalid ID.")
        return
    ok = delete_event(eid)
    print("Deleted." if ok else "Not found.")


def admin_menu() -> None:
    while True:
        print("\nAdmin Menu")
        print("1) Create event")
        print("2) List events")
        print("3) Delete event")
        print("0) Back")
        choice = input("Select: ").strip()
        if choice == "1":
            admin_create_event()
            pause()
        elif choice == "2":
            admin_list_events()
            pause()
        elif choice == "3":
            admin_delete_event()
            pause()
        elif choice == "0":
            return
        else:
            print("Invalid choice.")


# ---------- Customer workflow ----------

def customer_list_events() -> List[Event]:
    with get_session() as session:
        rows = session.scalars(
            select(Event).options(selectinload(Event.venue)).order_by(Event.start_at)
        ).all()
    if not rows:
        print("No events.")
        return []
    for e in rows:
        vname = e.venue.name if e.venue else "?"
        print(f"{e.id}: {e.name} — {vname} — {e.start_at.isoformat()}")
    return rows


def fetch_available_with_labels(event_id: int, limit: int | None = None) -> List[Tuple[EventSeat, str]]:
    with get_session() as session:
        q = (
            select(EventSeat)
            .where(EventSeat.event_id == event_id, EventSeat.status == "AVAILABLE")
            .options(selectinload(EventSeat.seat))
            .order_by(EventSeat.seat_id)
        )
        if isinstance(limit, int) and limit > 0:
            q = q.limit(limit)
        es_rows = session.scalars(q).all()
    labeled: List[Tuple[EventSeat, str]] = []
    for es in es_rows:
        seat = es.seat  # loaded by selectinload
        label = f"{seat.row}{seat.number}" if seat else f"seat#{es.seat_id}"
        labeled.append((es, label))
    return labeled


def customer_book_seats() -> None:
    rows = customer_list_events()
    if not rows:
        return
    eid_str = input_nonempty("Enter Event ID to book: ")
    try:
        event_id = int(eid_str)
    except ValueError:
        print("Invalid Event ID.")
        return

    # Show all available seats (no prompt)
    avail = fetch_available_with_labels(event_id, limit=None)
    if not avail:
        print("No available seats.")
        return

    print("\nAvailable seats:")
    for es, label in avail:
        print(f"EventSeat #{es.id} — {label} — KSh {es.price_ksh}")

    choice = input_nonempty("Enter EventSeat IDs or seat labels (comma-separated, e.g., '12,13' or 'A1,A2'): ")
    tokens = [t.strip() for t in choice.split(",") if t.strip()]

    label_map = {label.upper(): es.id for es, label in avail}
    to_sell_ids: List[int] = []
    for t in tokens:
        if t.isdigit():
            to_sell_ids.append(int(t))
        else:
            esid = label_map.get(t.upper())
            if esid:
                to_sell_ids.append(esid)

    if not to_sell_ids:
        print("No valid selections.")
        return

    # Fetch event name once for confirmation output
    with get_session() as session:
        ev = session.get(Event, event_id)
        event_name = ev.name if ev else f"Event {event_id}"

    # Build a map from the displayed avail list for quick labels, and fetch any missing details
    avail_map = {es.id: (es, label) for es, label in avail}
    missing_ids = [i for i in to_sell_ids if i not in avail_map]
    extra_map = {}
    if missing_ids:
        with get_session() as session:
            extra_rows = session.scalars(
                select(EventSeat)
                .where(EventSeat.event_id == event_id, EventSeat.id.in_(missing_ids))
                .options(selectinload(EventSeat.seat))
            ).all()
            for es in extra_rows:
                seat = es.seat
                label = f"{seat.row}{seat.number}" if seat else f"seat#{es.seat_id}"
                extra_map[es.id] = (es, label)

    sold = 0
    now = datetime.now(tz=timezone.utc)
    for esid in to_sell_ids:
        ok = sell_event_seat(esid)
        if ok:
            sold += 1
            es, label = avail_map.get(esid) or extra_map.get(esid, (None, f"#{esid}"))
            price = es.price_ksh if es else "?"
            print(f"Booked: '{event_name}' — Seat {label} — KSh {price} — at {now.isoformat()}")
        else:
            print(f"Could not book seat #{esid} (unavailable).")

    print(f"\nSOLD {sold}/{len(to_sell_ids)} seats.")


def customer_menu() -> None:
    while True:
        print("\nCustomer Menu")
        print("1) List events")
        print("2) Book available seats")
        print("0) Back")
        choice = input("Select: ").strip()
        if choice == "1":
            customer_list_events()
            pause()
        elif choice == "2":
            customer_book_seats()
            pause()
        elif choice == "0":
            return
        else:
            print("Invalid choice.")


# ---------- Main ----------

def main() -> None:
    while True:
        print("\nMain Menu")
        print("1) Admin")
        print("2) Customer")
        print("0) Exit")
        choice = input("Select: ").strip()
        if choice == "1":
            admin_menu()
        elif choice == "2":
            customer_menu()
        elif choice == "0":
            print("Bye.")
            return
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()