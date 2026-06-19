import sys
from pathlib import Path

# Allow running this script directly from backend/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.main import seed


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
