"""Kurum kaydı ve oturum işlemleri.

Her kullanıcı tam olarak bir kuruma aittir; başka bir kurumda çalışmak için
ayrı hesap açmak gerekir. Bu yüzden e-posta sistem genelinde eşsizdir.

Herkese açık kayıt `.env` içindeki `ALLOW_REGISTRATION` ile kapatılabilir.
Kapalıyken bile, sistemde hiç kurum yoksa ilk kayda izin verilir — aksi halde
yeni kurulum kilitlenirdi.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import aktif_kurum, current_user
from app.models import Institution, Term, User
from app.schemas import (
    AuthStatus, InstitutionOut, InstitutionUpdate, LoginRequest, RegisterRequest,
    Token, UserOut,
)
from app.security import create_access_token, hash_password, verify_password
from app.varsayilanlar import varsayilan_izgara

router = APIRouter(tags=["kurum ve oturum"])


def _kurum_var_mi(db: Session) -> bool:
    return db.scalar(select(Institution.id).limit(1)) is not None


@router.get("/auth/status", response_model=AuthStatus)
def durum(db: Session = Depends(get_db)) -> AuthStatus:
    var = _kurum_var_mi(db)
    return AuthStatus(
        has_institutions=var,
        registration_open=settings.allow_registration or not var,
    )


@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def kayit_ol(payload: RegisterRequest, db: Session = Depends(get_db)) -> Token:
    """Yeni kurum açar, ilk kullanıcıyı ve ilk dönemi oluşturur."""
    ilk_kurulum = not _kurum_var_mi(db)
    if not settings.allow_registration and not ilk_kurulum:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Bu sunucuda yeni kurum kaydı kapalı. Sunucu yöneticinize başvurun.",
        )
    if db.scalar(select(User.id).where(User.email == payload.email.lower())):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu e-posta zaten kayıtlı. Her hesap yalnızca bir kuruma bağlanabilir; "
            "başka bir kurum için farklı bir e-posta kullanın.",
        )

    kurum = Institution(name=payload.institution_name, type=payload.institution_type)
    db.add(kurum)
    db.flush()

    donem = Term(institution_id=kurum.id, name=payload.term_name)
    db.add(donem)
    db.flush()
    kurum.active_term_id = donem.id
    varsayilan_izgara(db, donem)

    user = User(
        institution_id=kurum.id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
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
def kurum_bilgisi(inst: Institution = Depends(aktif_kurum)) -> Institution:
    return inst


@router.put("/institution", response_model=InstitutionOut)
def kurum_guncelle(
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    inst: Institution = Depends(aktif_kurum),
) -> Institution:
    inst.name, inst.type, inst.address = payload.name, payload.type, payload.address
    db.commit()
    db.refresh(inst)
    return inst
