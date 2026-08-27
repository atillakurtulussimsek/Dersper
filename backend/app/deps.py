"""Ortak bağımlılıklar: oturum doğrulama."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
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
