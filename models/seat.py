"""
create the seats table
each seat belongs to a venue
unique seat per venue by (row, number)
"""
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from db.base import Base

if TYPE_CHECKING:
    # for type checkers only; avoids circular import at runtime
    from models.event_seat import EventSeat
    from models.venue import Venue


class Seat(Base):
    __tablename__ = "seats"

    #relationships
    venue: Mapped["Venue"] = relationship(back_populates="seats")
    event_seats: Mapped[List["EventSeat"]] = relationship(
        back_populates="seat", cascade="all, delete-orphan"
    )


    



    __table_args__ = (
        #prevent the table from having dupicate seat positions
        UniqueConstraint("venue_id", "row", "number"),
    )
    #cascade so that deleting a venue deletes its seats
    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"), index=True, nullable = False
    )
    #venue seat format
    # Human-friendly position (e.g., row "A", number 12)
    row: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


    #debugging
    def __repr__(self) -> str:
        return f"Seat(id={self.id!r}, venue_id={self.venue_id!r}, pos={self.row}{self.number})"