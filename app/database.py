import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variable or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL")

# If no DATABASE_URL is provided or there's an issue with PostgreSQL,
# use SQLite as a fallback for development
if not DATABASE_URL:
    SQLITE_URL = "sqlite:///./tradeeasy.db"
    print(f"No DATABASE_URL found, using SQLite: {SQLITE_URL}")
    engine = create_engine(
        SQLITE_URL, connect_args={"check_same_thread": False}
    )
else:
    try:
        # Attempt to create PostgreSQL engine
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        # Fall back to SQLite
        SQLITE_URL = "sqlite:///./tradeeasy.db"
        print(f"Falling back to SQLite: {SQLITE_URL}")
        engine = create_engine(
            SQLITE_URL, connect_args={"check_same_thread": False}
        )

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models using the updated method
Base = declarative_base()

# Dependency to get DB session
def get_db():
    """
    Dependency function that yields a SQLAlchemy database session.
    This session is automatically closed when the request is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
