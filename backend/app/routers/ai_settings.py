"""Yapay zeka ayarları. Anahtar veritabanına şifrelenmiş yazılır, geri okunmaz."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import client as ai
from app.crypto import decrypt, encrypt, mask
from app.db import get_db
from app.deps import current_user
from app.models import AiSettings
from app.schemas import AiSettingsIn, AiSettingsOut, AiTestResult

router = APIRouter(prefix="/ai", tags=["yapay zeka"],
                   dependencies=[Depends(current_user)])


def _ayar(db: Session) -> AiSettings:
    a = db.scalar(select(AiSettings).limit(1))
    if a is None:
        a = AiSettings()
        db.add(a)
        db.commit()
        db.refresh(a)
    return a


def _cikti(a: AiSettings) -> AiSettingsOut:
    anahtar = decrypt(a.api_key_encrypted) if a.api_key_encrypted else ""
    return AiSettingsOut(
        enabled=a.enabled,
        base_url=a.base_url,
        model=a.model,
        api_key_masked=mask(anahtar),
        has_api_key=bool(anahtar),
    )


@router.get("/settings", response_model=AiSettingsOut)
def ayarlar(db: Session = Depends(get_db)) -> AiSettingsOut:
    return _cikti(_ayar(db))


@router.put("/settings", response_model=AiSettingsOut)
def ayarlari_kaydet(payload: AiSettingsIn, db: Session = Depends(get_db)) -> AiSettingsOut:
    a = _ayar(db)
    a.enabled = payload.enabled
    a.base_url = (payload.base_url or "").strip() or None
    a.model = payload.model.strip() or "gpt-4o-mini"
    if payload.api_key:
        a.api_key_encrypted = encrypt(payload.api_key.strip())
    db.commit()
    db.refresh(a)
    return _cikti(a)


@router.delete("/settings/key", response_model=AiSettingsOut)
def anahtari_sil(db: Session = Depends(get_db)) -> AiSettingsOut:
    a = _ayar(db)
    a.api_key_encrypted = None
    a.enabled = False
    db.commit()
    db.refresh(a)
    return _cikti(a)


@router.post("/test", response_model=AiTestResult)
def test(db: Session = Depends(get_db)) -> AiTestResult:
    ok, mesaj = ai.baglanti_testi(_ayar(db))
    return AiTestResult(ok=ok, message=mesaj)
