"""Administrator-only, read-only final project evidence snapshot."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import require_roles
from ..config import get_settings
from ..operations.routes import overview
from ..assurance.policy import evaluate_config
from .evaluation import evaluate

router = APIRouter(prefix='/release', tags=['P20 Final Evaluation'])

@router.get('/snapshot')
def snapshot(db: Session = Depends(get_db), user=Depends(require_roles('Administrator'))):
    # No credentials, raw event payloads or attacker commands are returned.
    # The existing bounded P18 aggregator is the authoritative metrics source.
    data = overview(db=db, user=user)
    settings = get_settings()
    checks = [x for x in evaluate_config(settings.allowed_origins, False, 'development') if x['id'] != 'debug_disabled']
    return evaluate(data, checks)
