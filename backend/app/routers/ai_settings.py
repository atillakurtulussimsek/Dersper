"""Yapay zeka ayarları. Anahtar veritabanına şifrelenmiş yazılır, geri okunmaz."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import client as ai
from app.crypto import decrypt, encrypt, mask
from app.db import get_db
from app.deps import current_user
from app.models import AiSettings
from app.schemas import (
    AiModelsIn, AiModelsOut, AiSettingsIn, AiSettingsOut, AiTestResult,
)

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


VARSAYILAN_ADRES = "https://api.openai.com/v1"


@router.post("/models", response_model=AiModelsOut)
def modeller(payload: AiModelsIn, db: Session = Depends(get_db)) -> AiModelsOut:
    """Sağlayıcıdaki modelleri listeler; aynı zamanda adres ve anahtarı doğrular."""
    ayar = _ayar(db)
    try:
        liste = ai.modelleri_getir(ayar, payload.base_url, payload.api_key)
    except ai.AiKapali as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Model listesi alınamadı. Adresi ve anahtarı kontrol edin. Ayrıntı: {e}",
        )
    if not liste:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Sağlayıcı boş bir model listesi döndürdü.",
        )
    adres = payload.base_url if payload.base_url is not None else ayar.base_url
    return AiModelsOut(models=liste, source=(adres or "").strip() or VARSAYILAN_ADRES)


@router.post("/test", response_model=AiTestResult)
def test(db: Session = Depends(get_db)) -> AiTestResult:
    ok, mesaj = ai.baglanti_testi(_ayar(db))
    return AiTestResult(ok=ok, message=mesaj)
