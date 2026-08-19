"""FastAPI dependency providers."""

from app.db.session import get_async_session

get_db = get_async_session

__all__ = ["get_db"]
