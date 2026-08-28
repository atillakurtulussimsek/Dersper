"""Test ortamı: geçici SQLite veritabanı. Gerçek veritabanına dokunulmaz."""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ENCRYPTION_KEY"] = "test-encryption"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
import app.models  # noqa: F401  — tabloların kaydolması için
from app.main import app


@pytest.fixture(autouse=True)
def _sema():
    """Her test kendi boş veritabanıyla başlar; testler birbirini etkilemez."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def uret_ve_bekle(c: TestClient, timetable_id: int, saniye: float = 60.0) -> dict:
    """Arka plan üretimini başlatır ve bitmesini bekler.

    Üretim artık eşzamansız çalıştığı için testler sonucu böyle okur.
    """
    import time

    r = c.post(f"/api/timetables/{timetable_id}/solve")
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]

    son = time.monotonic() + saniye
    while time.monotonic() < son:
        aktif = c.get(f"/api/timetables/{timetable_id}/runs/active").json()
        if aktif is None:
            break
        time.sleep(0.05)
    else:
        c.post(f"/api/timetables/{timetable_id}/runs/{run_id}/stop")
        raise AssertionError("Üretim süresi doldu.")

    return next(
        d for d in c.get(f"/api/timetables/{timetable_id}/runs").json()
        if d["id"] == run_id
    )


def cozumsuz_calistir(c: TestClient, timetable_id: int, saniye: float = 30.0) -> dict:
    """Yerleşemeyeceği bilinen bir üretimi başlatır, ilk raporu bekler, durdurur.

    Çözümsüz işler tasarım gereği kendiliğinden durmaz; test onları elle durdurur.
    """
    import time

    r = c.post(f"/api/timetables/{timetable_id}/solve")
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]

    son = time.monotonic() + saniye
    while time.monotonic() < son:
        aktif = c.get(f"/api/timetables/{timetable_id}/runs/active").json()
        if aktif is None:                       # kendiliğinden bitti
            break
        if aktif["attempts"] >= 1 and aktif["report"] is not None:
            break
        time.sleep(0.05)

    c.post(f"/api/timetables/{timetable_id}/runs/{run_id}/stop")
    son = time.monotonic() + saniye
    while time.monotonic() < son:
        if c.get(f"/api/timetables/{timetable_id}/runs/active").json() is None:
            break
        time.sleep(0.05)

    return next(
        d for d in c.get(f"/api/timetables/{timetable_id}/runs").json()
        if d["id"] == run_id
    )


@pytest.fixture
def istemci() -> TestClient:
    return TestClient(app)


@pytest.fixture
def yonetici(istemci: TestClient) -> TestClient:
    """Kurulumu tamamlanmış, oturum açmış istemci."""
    jeton = istemci.post("/api/setup", json={
        "institution_name": "Test Ortaokulu",
        "institution_type": "k12",
        "full_name": "Test Yönetici",
        "email": "yonetici@ornek.com",
        "password": "parola1234",
    }).json()["access_token"]
    istemci.headers["Authorization"] = f"Bearer {jeton}"
    return istemci
