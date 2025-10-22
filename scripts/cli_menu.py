from __future__ import annotations

"""
Text-menu CLI with Admin and Customer workflows.

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
from services.customer_service import get_or_create_customer
from services.booking import purchase_event_seats, finalize_held_seats
from services.eventseat_service import hold_event_seats


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
        print(f"The seats have been created successfully")

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
        print("Seat selection is not valid, please select a seat from the list ")
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

    # Place a 10-minute hold on selected seats (by seat_id) before payment
    seat_ids_to_hold: List[int] = []
    for esid in to_sell_ids:
        pair = avail_map.get(esid) or extra_map.get(esid)
        if pair:
            es, _ = pair
            seat_ids_to_hold.append(es.seat_id)

    held_eventseat_ids = hold_event_seats(event_id, seat_ids_to_hold, minutes=10)
    if not held_eventseat_ids:
        print("Could not place holds; seats may have been taken.")
        return

    # Recompute total from held items only
    held_map = {es.id: (es, lbl) for (es, lbl) in (avail + list(extra_map.values())) if es.id in held_eventseat_ids}
    total_amount = sum(es.price_ksh for es, _ in held_map.values())

    print("\nYour seats are on HOLD for 10 minutes:")
    for es, label in held_map.values():
        until = es.held_until.isoformat() if es.held_until else "in 10 minutes"
        print(f" - {label} — KSh {es.price_ksh} (held until {until})")
    print(f"Total: KSh {total_amount}")
    print("Pay with M-Pesa to Till No. 0000.")
    confirm = input_nonempty("Have you completed payment? (yes/no): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Payment not confirmed. Holds will expire automatically in 10 minutes.")
        return

    # Gather customer info
    cust_name = input_nonempty("Your name: ")
    cust_email = input_nonempty("Your email: ")
    cust_phone = input("Your phone (optional): ").strip() or None
    customer = get_or_create_customer(cust_name, cust_email, cust_phone)
    print(f"Customer ID: {customer.id}")

    # Purchase (create tickets) and print confirmations
    # Finalize purchase of held seats
    tickets = finalize_held_seats(event_id, held_eventseat_ids, customer.id)
    if not tickets:
        print("No seats could be booked (unavailable).")
        return

    print("")
    for ticket, label in tickets:
        when = ticket.purchased_at.isoformat()
        print(f"Booked: '{event_name}' — Seat {label} — KSh {ticket.price_ksh} — at {when} — Customer #{customer.id}")

    print(f"\nSOLD {len(tickets)}/{len(to_sell_ids)} seats.")


def customer_menu() -> None:
    while True:
        # Show events immediately when entering customer menu
        print("\nAvailable events:")
        customer_list_events()
        print("\nCustomer Menu")
        print("1) Book available seats")
        print("2) My bookings")
        print("0) Back")
        choice = input("Select: ").strip()
        if choice == "1":
            customer_book_seats()
            pause()
        elif choice == "2":
            customer_list_my_bookings()
            pause()
        elif choice == "0":
            return
        else:
            print("Invalid choice.")


def customer_reserve_and_pay() -> None:
    rows = customer_list_events()
    if not rows:
        return
    eid_str = input_nonempty("Enter Event ID to reserve: ")
    try:
        event_id = int(eid_str)
    except ValueError:
        print("Invalid Event ID.")
        return

    # Show available seats
    avail = fetch_available_with_labels(event_id, limit=None)
    if not avail:
        print("No available seats.")
        return

    print("\nAvailable seats:")
    for es, label in avail:
        print(f"EventSeat #{es.id} — {label} — KSh {es.price_ksh}")

    choice = input_nonempty("Enter seat labels or EventSeat IDs to reserve (comma-separated): ")
    tokens = [t.strip() for t in choice.split(",") if t.strip()]

    label_map = {label.upper(): es.seat_id for es, label in avail}
    to_hold_seat_ids: List[int] = []
    for t in tokens:
        if t.isdigit():
            # An EventSeat ID was given; map to its seat_id
            try:
                esid = int(t)
            except ValueError:
                continue
            es = next((es for es, _ in avail if es.id == esid), None)
            if es:
                to_hold_seat_ids.append(es.seat_id)
        else:
            sid = label_map.get(t.upper())
            if sid:
                to_hold_seat_ids.append(sid)

    if not to_hold_seat_ids:
        print("No valid selections.")
        return

    # Place holds for 10 minutes
    held_eventseat_ids = hold_event_seats(event_id, to_hold_seat_ids, minutes=10)
    if not held_eventseat_ids:
        print("Could not place holds (perhaps already taken).")
        return

    print("\nHOLD PLACED on the following EventSeat IDs:", held_eventseat_ids)
    print("Please make MPESA payment to Till No. 0000 now.")
    print("You have 10 minutes before the hold expires.")
    confirm = input_nonempty("Have you completed payment? (yes/no): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Payment not confirmed. Holds will expire automatically.")
        return

    # Gather customer info and finalize purchase
    cust_name = input_nonempty("Your name: ")
    cust_email = input_nonempty("Your email: ")
    cust_phone = input("Your phone (optional): ").strip() or None
    customer = get_or_create_customer(cust_name, cust_email, cust_phone)

    # Convert held EventSeat IDs into tickets
    tickets = purchase_event_seats(event_id, held_eventseat_ids, customer.id)
    if not tickets:
        print("Payment confirmed, but could not finalize tickets (holds may have expired).")
        return

    # Fetch event name for printing
    with get_session() as session:
        ev = session.get(Event, event_id)
        event_name = ev.name if ev else f"Event {event_id}"

    print("")
    for ticket, label in tickets:
        when = ticket.purchased_at.isoformat()
        print(f"TICKET: '{event_name}' — Seat {label} — KSh {ticket.price_ksh} — at {when} — Customer #{customer.id}")
    print(f"\nCONFIRMED: {len(tickets)} ticket(s). Thank you!")


def customer_list_my_bookings() -> None:
    email = input_nonempty("Enter your email to view bookings: ").strip().lower()
    with get_session() as session:
        from models.customer import Customer
        from models.ticket import Ticket
        cust = session.scalar(select(Customer).where(Customer.email == email))
        if not cust:
            print("No customer found for that email.")
            return
        rows = session.execute(
            select(Ticket, EventSeat)
            .join(EventSeat, EventSeat.id == Ticket.event_seat_id)
            .where(Ticket.customer_id == cust.id)
            .order_by(Ticket.purchased_at.desc())
        ).all()
        if not rows:
            print("You have no bookings.")
            return
        print(f"Customer #{cust.id} — {cust.name} <{cust.email}>")
        for ticket, es in rows:
            # Load event and seat label
            ev = session.get(Event, es.event_id)
            seat = es.seat if hasattr(es, "seat") else None
            if seat is None:
                seat = session.get(type(es).seat.property.mapper.class_, es.seat_id)  # fallback
            label = f"{seat.row}{seat.number}" if seat else f"seat#{es.seat_id}"
            when = ticket.purchased_at.isoformat()
            price = ticket.price_ksh
            ename = ev.name if ev else f"Event {es.event_id}"
            print(f"- {when} — {ename} — Seat {label} — KSh {price} — Ticket #{ticket.id}")


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