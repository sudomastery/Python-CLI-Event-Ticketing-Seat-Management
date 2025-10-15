# declarative mapping to venues tble
from typing import Optional


#Mapped/mapped_column privide type attributes for ORM columns
from sqlalchemy.orm import Mapped, mapped_column

#share base every model inherits from
from db.base import Base

#import the string column
from sqlalchemy import String

#create the table as class
class Venue(Base):
    #the actual table name
    __tablename__ = "venues"

    #pk
    id: Mapped[int] = mapped_column(primary_key=True)

    #name, unique and indexed
    name: Mapped[str] = mapped_column(String(200), unique = True, nullable= False, index=True)

    #address
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable = True)

    def __repr__(self) -> str:
        return f"Venue(id={self.id!r}, name={self.name!r}, address={self.address!r})"

