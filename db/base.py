# declarative base for ORM models - each table/class will inherit from this
from sqlalchemy.orm import DeclarativeBase


#Common parent for table classes
class Base(DeclarativeBase):
    pass