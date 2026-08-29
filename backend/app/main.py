"""Dersper — FastAPI uygulaması."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.solver.arkaplan import yarim_kalanlari_isaretle
from app.routers import (
    ai_settings, auth, catalog, exports, public, terms, timegrid, timetables,
    users,
)

@asynccontextmanager
async def yasam_dongusu(_: FastAPI):
    # Arka plan işleri uygulama süreciyle birlikte ölür; açık kalan
    # çalıştırma kayıtlarını kapat.
    yarim_kalanlari_isaretle()
    yield


app = FastAPI(
    lifespan=yasam_dongusu,
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

for r in (auth.router, users.router, terms.router, timegrid.router, catalog.router,
          timetables.router, exports.router, ai_settings.router, public.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["sistem"])
def saglik() -> dict:
    """Sürecin ayakta olduğunu bildirir. Veritabanına dokunmaz."""
    return {"status": "ok"}


@app.get("/api/health/db", tags=["sistem"])
def veritabani_saglik() -> dict:
    """Veritabanına gerçekten ulaşılabiliyor mu.

    Konteyner sağlık denetimi bunu kullanır: veritabanı erişilemezken servis
    'sağlıklı' görünüp isteklerde askıda kalmasın.
    """
    from sqlalchemy import text

    from app.db import engine

    try:
        with engine.connect() as baglanti:
            baglanti.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Veritabanına ulaşılamıyor: {type(e).__name__}: {str(e)[:200]}",
        )
    return {"status": "ok"}
