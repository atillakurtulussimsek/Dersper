"""Kurum kullanıcıları.

Rol ayrımı yoktur: kuruma eklenen herkes yöneticidir ve aynı yetkilere sahiptir.
Kullanıcılar yalnızca kendi kurumlarının hesaplarını görür ve yönetir.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import aktif_kurum, current_user
from app.models import Institution, User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["kullanıcılar"])


def _getir(db: Session, user_id: int, inst: Institution) -> User:
    u = db.get(User, user_id)
    if u is None or u.institution_id != inst.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kullanıcı bulunamadı.")
    return u


@router.get("", response_model=list[UserOut])
def kullanicilar(
    db: Session = Depends(get_db),
    inst: Institution = Depends(aktif_kurum),
    _: User = Depends(current_user),
) -> list[User]:
    return list(db.scalars(
        select(User).where(User.institution_id == inst.id).order_by(User.full_name)
    ))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def kullanici_ekle(
    payload: UserCreate,
    db: Session = Depends(get_db),
    inst: Institution = Depends(aktif_kurum),
    _: User = Depends(current_user),
) -> User:
    if db.scalar(select(User.id).where(User.email == payload.email.lower())):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu e-posta zaten kayıtlı. Bir hesap yalnızca bir kuruma bağlanabilir.",
        )
    u = User(
        institution_id=inst.id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.put("/{user_id}", response_model=UserOut)
def kullanici_guncelle(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    inst: Institution = Depends(aktif_kurum),
    ben: User = Depends(current_user),
) -> User:
    u = _getir(db, user_id, inst)
    if u.id == ben.id and not payload.is_active:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Kendi hesabınızı kapatamazsınız."
        )
    if not payload.is_active and _tek_aktif_mi(db, inst, u):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Kurumun son açık hesabı kapatılamaz.",
        )
    u.full_name = payload.full_name
    u.is_active = payload.is_active
    if payload.password:
        u.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(u)
    return u


def _tek_aktif_mi(db: Session, inst: Institution, u: User) -> bool:
    kalan = db.scalar(
        select(User.id).where(
            User.institution_id == inst.id, User.is_active.is_(True), User.id != u.id
        ).limit(1)
    )
    return kalan is None
