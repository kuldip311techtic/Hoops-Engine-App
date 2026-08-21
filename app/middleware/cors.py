"""CORS middleware wiring from settings (never '*' with credentials)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings


def add_cors(app: FastAPI, settings: Settings | None = None) -> None:
    """Register CORSMiddleware using configured origins."""
    cfg = settings or get_settings()
    origins = cfg.cors_origin_list or ["http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
