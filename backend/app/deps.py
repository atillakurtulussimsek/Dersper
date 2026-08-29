"""Ortak bağımlılıklar: oturum doğrulama, kurum yalıtımı ve aktif dönem.

Her kullanıcı tam olarak bir kuruma aittir. Uçların tamamı kullanıcının kendi
kurumuna göre süzülür; başka kurumun kaydına kimlikle bile erişilemez.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Institution, Term, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

YETKISIZ = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Oturum geçersiz veya süresi dolmuş.",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise YETKISIZ
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise YETKISIZ
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise YETKISIZ
    return user


def aktif_kurum(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Institution:
    """Oturum açan kullanıcının kurumu."""
    inst = db.get(Institution, user.institution_id)
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kurum bulunamadı.")
    return inst


def kurum(db: Session, user: User) -> Institution:
    """Bağımlılık dışından çağrılan sürüm."""
    inst = db.get(Institution, user.institution_id)
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kurum bulunamadı.")
    return inst


def aktif_donem(
    db: Session = Depends(get_db), inst: Institution = Depends(aktif_kurum)
) -> Term:
    """Kurumun üzerinde çalıştığı dönem. Tüm tanımlar buna göre süzülür.

    Aktif dönem silinmiş ya da hiç seçilmemişse, kurumun silinmemiş en yeni
    dönemi otomatik seçilir; hiç dönem yoksa çağıran yönlendirilir.
    """
    donem = db.get(Term, inst.active_term_id) if inst.active_term_id else None
    if donem is not None and not donem.is_deleted and donem.institution_id == inst.id:
        return donem

    donem = db.scalar(
        select(Term)
        .where(Term.institution_id == inst.id, Term.deleted_at.is_(None))
        .order_by(Term.id.desc())
        .limit(1)
    )
    if donem is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Hiç dönem tanımlı değil. Önce Dönemler bölümünden bir dönem oluşturun.",
        )
    inst.active_term_id = donem.id
    db.commit()
    return donem
