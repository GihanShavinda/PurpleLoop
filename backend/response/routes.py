"""P12: approved P11 dry-run rehearsal with audit and simulated rollback."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import User, SoarProposal, ResponseRehearsal, ResponseRehearsalAudit, AuditLog
from ..soar.playbooks import PLAYBOOKS
from .planner import make_plan

router=APIRouter(prefix='/response', tags=['P12 Response rehearsal (simulation only)'])
ROLES=('Administrator','Purple Team Engineer')
class Note(BaseModel):
    note: str = Field(min_length=10,max_length=1000)

def as_dict(r):
    return {k:getattr(r,k) for k in ('id','proposal_id','initiated_by','status','plan_json','created_at','rolled_back_by','rolled_back_at','rollback_note')}

def log(db,r,actor,action,note=''):
    db.add(ResponseRehearsalAudit(rehearsal_id=r.id,actor_id=actor.id,action=action,note=note))
    db.add(AuditLog(actor_id=actor.id,action='p12_'+action,resource='response_rehearsal',resource_id=r.id))

@router.get('/rehearsals')
def list_rehearsals(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(ResponseRehearsal).order_by(ResponseRehearsal.created_at.desc()).limit(100)).all()
    return [as_dict(x) for x in rows]

@router.get('/rehearsals/{rehearsal_id}/audit')
def audit(rehearsal_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if db.get(ResponseRehearsal,rehearsal_id) is None:raise HTTPException(404,'Rehearsal not found')
    rows=db.scalars(select(ResponseRehearsalAudit).where(ResponseRehearsalAudit.rehearsal_id==rehearsal_id).order_by(ResponseRehearsalAudit.created_at)).all()
    return [{'action':r.action,'note':r.note,'actor_id':r.actor_id,'created_at':r.created_at} for r in rows]

@router.post('/proposals/{proposal_id}/rehearse',status_code=201)
def rehearse(proposal_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles(*ROLES))):
    p=db.get(SoarProposal,proposal_id)
    if p is None:raise HTTPException(404,'Proposal not found')
    if p.status!='simulated' or p.approved_by is None:raise HTTPException(409,'Complete approved P11 simulation first')
    if p.proposed_by==p.approved_by:raise HTTPException(409,'Four-eyes approval required')
    if p.playbook_key not in PLAYBOOKS:raise HTTPException(422,'Unsupported playbook')
    existing=db.scalar(select(ResponseRehearsal).where(ResponseRehearsal.proposal_id==proposal_id).order_by(ResponseRehearsal.created_at.desc()).limit(1))
    if existing and existing.status=='rehearsed':raise HTTPException(409,'Active rehearsal already exists')
    # Strictly no infrastructure changes, even on approved proposals.
    try:plan=make_plan(p.playbook_key,p.id,p.incident_id,p.correlation_id)
    except ValueError as e:raise HTTPException(422,str(e)) from e
    r=ResponseRehearsal(proposal_id=p.id,initiated_by=user.id,status='rehearsed',plan_json=plan)
    db.add(r);db.flush();log(db,r,user,'rehearsed','No external actions performed');db.commit();db.refresh(r)
    return as_dict(r)

@router.post('/rehearsals/{rehearsal_id}/rollback')
def rollback(rehearsal_id:str,body:Note,db:Session=Depends(get_db),user:User=Depends(require_roles(*ROLES))):
    r=db.get(ResponseRehearsal,rehearsal_id)
    if r is None:raise HTTPException(404,'Rehearsal not found')
    if r.status!='rehearsed':raise HTTPException(409,'Only open rehearsals can be closed')
    r.status='rolled_back_simulation';r.rolled_back_by=user.id;r.rolled_back_at=datetime.now(timezone.utc);r.rollback_note=body.note.strip()
    log(db,r,user,'rolled_back_simulation',body.note.strip());db.commit();db.refresh(r)
    return as_dict(r)
