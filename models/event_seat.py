"""
EventSeat model (maps to 'event_seats' table).
- One row per seat for a specific event (availability + price).
- Unique per event/seat.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Interger, ForeignKey, UniqueConstraint, DateTime, Enum as SAEnum
from db.base import Base

class EventSeat(Base):
    __tablename__ = "event_seats"
