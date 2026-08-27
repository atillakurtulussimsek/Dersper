"""İlk kurulum sihirbazı ve oturum işlemleri.

Halka açık kayıt yoktur. İlk kurulumda kurum ve tek yönetici hesabı oluşturulur;
sonraki kullanıcıları yönetici açar.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.models import Day, Institution, Period, User
from app.schemas import (
    InstitutionOut, InstitutionUpdate, LoginRequest, SetupRequest, SetupStatus,
    Token, UserOut,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["kurulum"])

GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
VARSAYILAN_DERS_SAATI = 8


def _kurulum_tamam(db: Session) -> bool:
    return db.scalar(select(Institution.id).limit(1)) is not None


def _varsayilan_izgara(db: Session) -> None:
    """Pazartesi–Cuma, günde 8 ders saati. Kullanıcı sonra düzenler."""
    for i, ad in enumerate(GUN_ADLARI):
        gun = Day(index=i, name=ad, is_active=i < 5)
        db.add(gun)
        db.flush()
        if not gun.is_active:
            continue
        for p in range(VARSAYILAN_DERS_SAATI):
            db.add(Period(day_id=gun.id, index=p, name=f"{p + 1}. ders"))


@router.get("/setup/status", response_model=SetupStatus)
def kurulum_durumu(db: Session = Depends(get_db)) -> SetupStatus:
    return SetupStatus(completed=_kurulum_tamam(db))


@router.post("/setup", response_model=Token, status_code=status.HTTP_201_CREATED)
def kurulumu_tamamla(payload: SetupRequest, db: Session = Depends(get_db)) -> Token:
    if _kurulum_tamam(db):
        raise HTTPException(status.HTTP_409_CONFLICT, "Kurulum zaten tamamlanmış.")

    db.add(Institution(name=payload.institution_name, type=payload.institution_type))
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    _varsayilan_izgara(db)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.id))


@router.post("/auth/login", response_model=Token)
def giris(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-posta veya parola hatalı.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hesabınız kapalı.")
    return Token(access_token=create_access_token(user.id))


@router.get("/auth/me", response_model=UserOut)
def ben(user: User = Depends(current_user)) -> User:
    return user


@router.get("/institution", response_model=InstitutionOut)
def kurum(db: Session = Depends(get_db), _: User = Depends(current_user)) -> Institution:
    inst = db.scalar(select(Institution).limit(1))
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kurum bulunamadı.")
    return inst


@router.put("/institution", response_model=InstitutionOut)
def kurum_guncelle(
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> Institution:
    inst = db.scalar(select(Institution).limit(1))
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kurum bulunamadı.")
    inst.name, inst.type, inst.address = payload.name, payload.type, payload.address
    db.commit()
    db.refresh(inst)
    return inst
