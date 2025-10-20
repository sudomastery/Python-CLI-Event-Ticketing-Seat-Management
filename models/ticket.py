from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from .customer import Customer
    from .event_seat import EventSeat


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("event_seat_id", name="uq_ticket_event_seat"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    event_seat_id: Mapped[int] = mapped_column(ForeignKey("event_seats.id", ondelete="CASCADE"))

    price_ksh: Mapped[int]
    purchased_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(tz=timezone.utc))

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    event_seat: Mapped["EventSeat"] = relationship()

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} event_seat_id={self.event_seat_id} customer_id={self.customer_id}>"
