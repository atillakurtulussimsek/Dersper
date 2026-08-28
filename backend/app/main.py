"""Dersper — FastAPI uygulaması."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    ai_settings, catalog, exports, public, setup, terms, timegrid, timetables,
)

app = FastAPI(
    title="Dersper",
    description="Okullar için açık kaynaklı ders dağıtım programı.",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (setup.router, terms.router, timegrid.router, catalog.router,
          timetables.router, exports.router, ai_settings.router, public.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["sistem"])
def saglik() -> dict:
    return {"status": "ok"}
