"""Veritabanı oturumu ve taban model sınıfı."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings

def _baglanti_ayarlari() -> dict:
    """Sürücüye özel bağlantı seçenekleri.

    MySQL'de zaman aşımı verilmezse, erişilemeyen bir sunucuya yapılan bağlantı
    TCP zaman aşımına kadar (dakikalarca) askıda kalır; istek de öyle. Kısa bir
    sınır, sorunu askıda kalma yerine açık bir hataya çevirir.
    """
    if settings.database_url.startswith("mysql"):
        return {"connect_timeout": 10, "read_timeout": 60, "write_timeout": 60}
    return {}


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # uzak sunucuda kopan bağlantıları sessizce yeniler
    pool_recycle=1800,
    connect_args=_baglanti_ayarlari(),
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
