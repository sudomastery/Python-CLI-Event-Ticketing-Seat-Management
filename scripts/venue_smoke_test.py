"""
End-to-end smoke test for the Venue model.

- Opens a Session.
- Inserts a Venue row.
- Queries it back and prints it.
- Shows the SQL in the terminal (because SQL_ECHO=true).
"""
from sqlalchemy import select

from db import get_session
from models.venue import Venue  # ensure model is imported

def main() -> None:
    # Insert a venue
    with get_session() as session:
        v = Venue(name="Nyayo National Stadium", address="junction Nyayo Stadium, Aerodrome roads, Nairobi")
        session.add(v)
        # commit happens automatically via get_session() on success

    # Query it back
    with get_session() as session:
        stmt = select(Venue).where(Venue.name == "Sample Hall")
        row = session.scalars(stmt).first()
        print("Fetched:", row)

if __name__ == "__main__":
    main()