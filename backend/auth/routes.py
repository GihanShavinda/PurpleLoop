from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Role, RefreshSession, AuditLog
from ..schemas import RegisterInput, LoginInput, RefreshInput
from ..config import get_settings
from .security import hash_password, verify_password, issue_token, decode_token, token_hash, current_user

router = APIRouter(prefix='/auth', tags=['auth'])

def user_response(u):
    return {'id':u.id,'email':u.email,'role_name':u.role.name,'is_active':u.is_active}

def token_pair(db, user):
    s = get_settings()
    refresh = issue_token(user.id, 'refresh', s.refresh_token_days * 24 * 60)
    db.add(RefreshSession(user_id=user.id, token_hash=token_hash(refresh), expires_at=datetime.now(timezone.utc)+timedelta(days=s.refresh_token_days)))
    db.commit()
    return {'access_token': issue_token(user.id,'access',s.access_token_minutes), 'refresh_token':refresh,'token_type':'bearer'}

@router.post('/register', status_code=201)
def register(payload: RegisterInput, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email is already registered')
    viewer = db.scalar(select(Role).where(Role.name=='Viewer'))
    if not viewer:
        raise HTTPException(503, 'Roles not seeded; run seed command')
    user = User(email=email, password_hash=hash_password(payload.password), role_id=viewer.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_response(user)

@router.post('/login')
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email==str(payload.email).lower()))
    if not user or not user.is_active or not verify_password(payload.password,user.password_hash):
        raise HTTPException(401,'Invalid credentials')
    return token_pair(db,user)

@router.post('/refresh')
def refresh(payload: RefreshInput, db: Session = Depends(get_db)):
    claims = decode_token(payload.refresh_token,'refresh')
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash==token_hash(payload.refresh_token)).with_for_update())
    if not session or session.revoked or session.user_id != claims['sub'] or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(401,'Refresh token revoked or expired')
    user = db.get(User,session.user_id)
    if not user or not user.is_active:
        raise HTTPException(401,'Inactive account')
    session.revoked = True
    db.flush()
    return token_pair(db,user)

@router.post('/logout', status_code=204)
def logout(payload: RefreshInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash==token_hash(payload.refresh_token)))
    if session and session.user_id == user.id:
        session.revoked = True
        db.commit()

@router.get('/me')
def me(user: User = Depends(current_user)):
    return user_response(user)
