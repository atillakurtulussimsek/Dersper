"""Ortak bağımlılıklar: oturum doğrulama ve aktif dönem."""
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


def kurum(db: Session) -> Institution:
    inst = db.scalar(select(Institution).limit(1))
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kurum bulunamadı.")
    return inst


def aktif_donem(
    db: Session = Depends(get_db), _: User = Depends(current_user)
) -> Term:
    """Üzerinde çalışılan dönem. Tüm tanımlar buna göre süzülür.

    Aktif dönem silinmiş ya da hiç seçilmemişse, silinmemiş en yeni dönem
    otomatik seçilir; hiç dönem yoksa çağıran yönlendirilir.
    """
    inst = kurum(db)
    donem = db.get(Term, inst.active_term_id) if inst.active_term_id else None
    if donem is not None and not donem.is_deleted:
        return donem

    donem = db.scalar(
        select(Term).where(Term.deleted_at.is_(None)).order_by(Term.id.desc()).limit(1)
    )
    if donem is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Hiç dönem tanımlı değil. Önce Dönemler bölümünden bir dönem oluşturun.",
        )
    inst.active_term_id = donem.id
    db.commit()
    return donem
