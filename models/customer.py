from __future__ import annotations

from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from .ticket import Ticket


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(tz=timezone.utc))

    tickets: Mapped[List["Ticket"]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name!r} email={self.email!r}>"
