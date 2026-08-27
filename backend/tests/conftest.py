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
