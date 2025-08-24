from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import Config
from .models import Base   # ✅ import Base from models.py

# --- Engine ---
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    future=True,
    **Config.SQLALCHEMY_ENGINE_OPTIONS
)

# --- Session factory ---
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)

# --- Dependency for DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Cleanup ---
def shutdown_session(exception=None):
    SessionLocal.remove()
    engine.dispose()
