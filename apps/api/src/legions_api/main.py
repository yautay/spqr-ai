"""FastAPI application entrypoint for Legions backend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from legions_api.api.routes.game import router as game_router
from legions_api.core.tables.loader import load_supported_tables
from legions_api.logging import configure_logging

configure_logging()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Emit startup diagnostics and keep lifecycle hooks centralized."""

    loaded_tables = load_supported_tables()
    logger.info("Loaded {} rules tables", len(loaded_tables))
    logger.info("Legions API startup complete")
    yield


app = FastAPI(title="Legions API", version="0.1.0", lifespan=lifespan)
app.include_router(game_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Basic health endpoint for local checks and CI smoke tests."""

    logger.debug("Health check requested")
    return {"status": "ok"}
