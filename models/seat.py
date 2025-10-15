"""
create the seats table
each seat belongs to a venue
unique seat per venue by (row, number)
"""
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from db.base import Base


class Sear(Base):
    __tablename__ = "seats"
    __table_args__ = (
        #prevent the table from having dupicate seat positions
    )
