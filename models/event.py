"""
event model maps to events table
- Each event belongs to a venue.
"""
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey
from db.base import Base
from datetime import datetime

if TYPE_CHECKING:
    # type-only imports to avoid circular imports at runtime
    from models.venue import Venue
    from models.event_seat import EventSeat


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)

    #fk to venues id, deleting a venue deletes its events
    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"), index=True, nullable=False
      
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    #starttime

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="events")
    event_seats: Mapped[List["EventSeat"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    #nullable description/ advertisement
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True )