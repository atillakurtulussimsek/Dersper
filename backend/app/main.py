"""Dersper — FastAPI uygulaması.

Üretimde derlenmiş arayüz de bu uygulama tarafından sunulur (`app/static`).
Böylece tek konteyner, tek alan adı yeter: ayrı bir web sunucusuna, konteynerler
arası ağa ve CORS ayarına gerek kalmaz. Klasör yoksa yalnızca API çalışır ve
arayüz geliştirmede Vite'ın kendi sunucusundan gelir.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    # Sürüm numarasının kaynağı frontend/package.json — arayüzdeki rozet
    # oradan gömülür. Sürüm yükseltilirken bu satır da birlikte güncellenir.
    version="0.9.0",
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


# --- Derlenmiş arayüz ---

ARAYUZ = Path(__file__).resolve().parent / "static"

if (ARAYUZ / "index.html").is_file():
    # Varlıklar adlarında özet taşır; uzun süre önbelleklenebilirler.
    if (ARAYUZ / "assets").is_dir():
        app.mount(
            "/assets", StaticFiles(directory=ARAYUZ / "assets"), name="assets"
        )

    @app.get("/{yol:path}", include_in_schema=False)
    def arayuz(yol: str) -> FileResponse:
        """Tek sayfa uygulaması: bilinmeyen yollar index.html'e düşer.

        /kayit, /programlar/3 gibi adreslerin sunucuda karşılığı yoktur;
        yönlendirmeyi tarayıcıdaki uygulama yapar. API yolları bu noktaya
        gelmeden önce eşleştiği için buraya yalnızca arayüz istekleri düşer.
        """
        if yol.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bilinmeyen API ucu.")
        dosya = ARAYUZ / yol
        if yol and dosya.is_file():
            return FileResponse(dosya)
        return FileResponse(ARAYUZ / "index.html")
