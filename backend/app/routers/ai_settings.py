"""Yapay zeka ayarları. Anahtar veritabanına şifrelenmiş yazılır, geri okunmaz."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import client as ai
from app.crypto import decrypt, encrypt, mask
from app.db import get_db
from app.deps import aktif_kurum, current_user
from app.models import AiSettings, Institution
from app.schemas import (
    AiModelsIn, AiModelsOut, AiSettingsIn, AiSettingsOut, AiTestResult,
)

router = APIRouter(prefix="/ai", tags=["yapay zeka"],
                   dependencies=[Depends(current_user)])


def _ayar(db: Session, inst: Institution) -> AiSettings:
    """Kurumun yapay zeka ayarı; yoksa oluşturulur."""
    a = db.scalar(select(AiSettings).where(AiSettings.institution_id == inst.id))
    if a is None:
        a = AiSettings(institution_id=inst.id)
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
def ayarlar(
    db: Session = Depends(get_db), inst: Institution = Depends(aktif_kurum)
) -> AiSettingsOut:
    return _cikti(_ayar(db, inst))


@router.put("/settings", response_model=AiSettingsOut)
def ayarlari_kaydet(
    payload: AiSettingsIn,
    db: Session = Depends(get_db),
    inst: Institution = Depends(aktif_kurum),
) -> AiSettingsOut:
    a = _ayar(db, inst)
    a.enabled = payload.enabled
    a.base_url = (payload.base_url or "").strip() or None
    a.model = payload.model.strip() or "gpt-4o-mini"
    if payload.api_key:
        a.api_key_encrypted = encrypt(payload.api_key.strip())
    db.commit()
    db.refresh(a)
    return _cikti(a)


@router.delete("/settings/key", response_model=AiSettingsOut)
def anahtari_sil(
    db: Session = Depends(get_db), inst: Institution = Depends(aktif_kurum)
) -> AiSettingsOut:
    a = _ayar(db, inst)
    a.api_key_encrypted = None
    a.enabled = False
    db.commit()
    db.refresh(a)
    return _cikti(a)


VARSAYILAN_ADRES = "https://api.openai.com/v1"


@router.post("/models", response_model=AiModelsOut)
def modeller(
    payload: AiModelsIn,
    db: Session = Depends(get_db),
    inst: Institution = Depends(aktif_kurum),
) -> AiModelsOut:
    """Sağlayıcıdaki modelleri listeler; aynı zamanda adres ve anahtarı doğrular."""
    ayar = _ayar(db, inst)
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
def test(
    db: Session = Depends(get_db), inst: Institution = Depends(aktif_kurum)
) -> AiTestResult:
    ok, mesaj = ai.baglanti_testi(_ayar(db, inst))
    return AiTestResult(ok=ok, message=mesaj)
