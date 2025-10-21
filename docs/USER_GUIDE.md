# Python CLI Event Ticketing & Seat Management — User Guide

This guide explains how to set up, run, and use the CLI-based event ticketing system. It also covers the data model, services, and common workflows for admins and customers.

## Overview

- Tech: Python 3.13, SQLAlchemy 2.x, Postgres (psycopg3)
- Structure: Venue → Seats (physical layout) → Event → EventSeat (per-event capacity & status) → Ticket (sold seat per customer)
- Status flow: AVAILABLE → HELD (optional hold) → SOLD

## Getting Started

1) Configure environment
- Edit `config.py` or set env vars:
  - `DATABASE_URL`: e.g., `postgresql+psycopg://user:pass@localhost:5432/mydb`
  - `SQL_ECHO=false` (recommended for CLI)

2) Create database tables
- From project root:
```
python -m scripts.bootstrap_db
```
- Output shows DB version and creates any missing tables (idempotent).

3) Run the CLI
- From project root:
```
python -m scripts.cli_menu
```

## Concepts

- Venue (`models/venue.py`)
  - A location that contains Seats and hosts Events.
- Seat (`models/seat.py`)
  - Physical seat in a Venue; unique by (venue_id, row, number). Example label: `A10`.
- Event (`models/event.py`)
  - A show at a Venue with a start datetime.
- EventSeat (`models/event_seat.py`)
  - Per-event seat record: status, price, held_until. Unique by (event_id, seat_id).
- Customer (`models/customer.py`)
  - Person who buys tickets; unique email.
- Ticket (`models/ticket.py`)
  - A purchased EventSeat linked to a Customer with price and purchased_at.

## Admin Workflow

1) Create an event
- Menu: Main → Admin → Create event
- Steps:
  - Enter venue name (and address if creating it).
  - Enter event name, start in N days (default 7), optional description.
  - Enter capacity (default 50). The CLI ensures a simple grid for the Venue:
    - 10 seats per row, rows added as A, B, C… to cover capacity.
  - Enter price (default KSh 1500).
  - The system seeds EventSeat rows up to the capacity.

2) List events
- Menu: Main → Admin → List events
- Shows: `id: name — venue — start_at [seats: available/total available]`

3) Delete event
- Menu: Main → Admin → Delete event
- Deletes by Event ID.

## Customer Workflow

1) Browse events
- Menu: Main → Customer → List events

2) Book seats
- Menu: Main → Customer → Book available seats
- Steps:
  - Enter Event ID.
  - CLI lists all available seats with labels and prices.
  - Enter desired seats by EventSeat IDs or labels (e.g., `12,13` or `A1,A2`).
  - Enter your name, email, and optional phone.
  - System sells available seats and creates Tickets; prints a confirmation per seat:
    - Event name, seat label, price, purchase time, and your Customer ID.

3) My bookings
- Menu: Main → Customer → My bookings
- Enter your email to see your tickets listed with event, seat, price, time, and ticket id.

## Services & Behavior

- Seat seeding (`services/seat_service.py`)
  - `ensure_grid(venue_id, rows, numbers)`: Creates missing Seat rows.
- Event seat setup (`services/eventseat_setup_service.py`)
  - `seed_event_seats(event_id, venue_id, price_ksh, only_missing=True, seat_limit=None)`
  - Deterministic order (row A..Z, number ascending). `seat_limit` sets per-event capacity.
- Availability & booking (`services/eventseat_service.py` and `services/booking.py`)
  - List available: seats with status `AVAILABLE`.
  - Purchase: marks seat `SOLD`, creates `Ticket` for the `Customer`.
- Customers (`services/customer_service.py`)
  - `get_or_create_customer(name, email, phone)` ensures unique customers by email and updates name/phone.

## Notes

- Event capacity is implemented by how many EventSeat rows are seeded for an event (Seat table remains venue-wide).
- Holds: The system supports HELD states and expiry in services if you later enable timed reservations.
- Logging: CLI disables SQL logs for a clean experience.

## Troubleshooting

- No available seats after creating an event:
  - Ensure the venue has seats; the Admin create flow auto-creates the grid for the requested capacity.
  - Admin → List events shows available/total; total 0 means you didn’t seed EventSeat rows.
- Duplicate event seat labels:
  - Seat labels are per venue; labels repeat across different events but refer to distinct EventSeat records.
- Customer not found in My bookings:
  - Use the same email you used while booking.

## Data Model Quick Reference

- EventSeat.status: `AVAILABLE`, `HELD`, `SOLD`
- Uniqueness:
  - Seat: (venue_id, row, number)
  - EventSeat: (event_id, seat_id)
  - Ticket: event_seat_id (unique)
  - Customer: email (unique)

## Extending

- Group orders: Add an `orders` table and associate many `tickets` per order.
- Payments: Add payment status, method, and references to `tickets` or a new `payments` table.
- Validation: Add stricter email/phone validation in the CLI.
