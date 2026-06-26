"""
Database engine + session dependency for FastAPI routes.
"""
from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db():
    """Create tables if they don't exist. Call once on app startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per-request."""
    with Session(engine) as session:
        yield session