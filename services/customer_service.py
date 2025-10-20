from __future__ import annotations

from sqlalchemy import select

from db import get_session
from models.customer import Customer


def get_or_create_customer(name: str, email: str, phone: str | None = None) -> Customer:
    email = email.strip().lower()
    with get_session() as session:
        existing = session.scalar(select(Customer).where(Customer.email == email))
        if existing:
            # Update name/phone if provided
            changed = False
            if name and existing.name != name:
                existing.name = name
                changed = True
            if phone and existing.phone != phone:
                existing.phone = phone
                changed = True
            if changed:
                session.flush()
            return existing

        cust = Customer(name=name, email=email, phone=phone)
        session.add(cust)
        session.flush()
        return cust
