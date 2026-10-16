from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import get_settings
from ..models import User

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

def hash_password(value: str) -> str:
    return password_hasher.hash(value)

def verify_password(value: str, hashed: str) -> bool:
    return password_hasher.verify(value, hashed)

def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()

def issue_token(user_id: str, kind: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': user_id, 'type': kind, 'iat': now, 'exp': now + timedelta(minutes=minutes), 'jti': str(uuid4())}
    s = get_settings()
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)

def decode_token(token: str, kind: str) -> dict:
    s = get_settings()
    try:
        data = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], options={'require':['sub','type','exp','jti']})
        if data['type'] != kind:
            raise InvalidTokenError('wrong token type')
        return data
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Authentication required', headers={'WWW-Authenticate':'Bearer'})
    user = db.get(User, decode_token(credentials.credentials, 'access')['sub'])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail='Inactive or missing account')
    return user

def require_roles(*roles: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role.name not in roles:
            raise HTTPException(status_code=403, detail='Insufficient privileges')
        return user
    return guard
