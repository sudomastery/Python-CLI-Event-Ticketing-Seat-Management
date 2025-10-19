"""
event model maps to events table
- Each event belongs to a venue.
"""
from typing import Optional 
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey
from db.base import Base