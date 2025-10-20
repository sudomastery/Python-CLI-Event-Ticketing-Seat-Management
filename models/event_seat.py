"""
EventSeat model (maps to 'event_seats' table).
- One row per seat for a specific event (availability + price).
- Unique per event/seat.
"""
from typing import Optional
from datetime import datetime


from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey, UniqueConstraint, DateTime, Enum as SAEnum
from db.base import Base

class EventSeat(Base):
    __tablename__ = "event_seats"
    #prevent the same seat from appearing twice for the same event
    __table_args__ = (UniqueConstraint("event_id", "seat_id"),)



    id: Mapped[int] = mapped_column(primary_key=True)

    #fk to event id
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )

    seat_id: Mapped[int] = mapped_column(
        ForeignKey("seats.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(
        SAEnum("AVAILABLE", "HELD", "SOLD", name="eventseat_status", native_enum=False),
        default="AVAILABLE", 
        nullable=False,
        index=True,


    )

    price_ksh: Mapped[int] = mapped_column(Integer, nullable=False)

    #when a seat is temporarily held
    held_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Relationships
    event: Mapped["Event"] = relationship(back_populates="event_seats")
    seat: Mapped["Seat"] = relationship(back_populates="event_seats")
