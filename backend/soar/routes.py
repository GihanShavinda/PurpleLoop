"""Manually triggered P11 SOAR. Every transition logged. No real execution."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import User, IncidentCase, CorrelationCase, SoarProposal, SoarAudit, AuditLog
from .playbooks import PLAYBOOKS, simulate

router=APIRouter(prefix='/soar',tags=['P11 SOAR (dry-run)'])
PROPOSERS=('Administrator','Purple Team Engineer','SOC Analyst','Detection Engineer')
APPROVERS=('Administrator','Purple Team Engineer')

class ProposalIn(BaseModel):
    playbook_key: str
    justification: str = Field(min_length=10,max_length=2000)
    incident_id: str | None = None
    correlation_id: str | None = None
    @model_validator(mode='after')
    def one_target(self):
        if (self.incident_id is None)==(self.correlation_id is None):
            raise ValueError('Select exactly one incident or correlation case')
        return self
class DecisionIn(BaseModel):
    note: str = Field(min_length=5,max_length=2000)

def record(db, proposal, actor, action, detail=''):
    db.add(SoarAudit(proposal_id=proposal.id,actor_id=actor.id,action=action,detail=detail))
    db.add(AuditLog(actor_id=actor.id,action='p11_'+action,resource='soar_proposal',resource_id=proposal.id))
def output(p):
    return {k:getattr(p,k) for k in ('id','playbook_key','incident_id','correlation_id','justification','status','proposed_by','approved_by','decision_note','output_json','created_at','decided_at','executed_at')}

@router.get('/playbooks')
def playbooks(user:User=Depends(current_user)):
    return [{'key':k, **v,'mode':'dry_run'} for k,v in PLAYBOOKS.items()]
@router.get('/proposals')
def proposals(db:Session=Depends(get_db), user:User=Depends(current_user)):
    rows=db.scalars(select(SoarProposal).order_by(SoarProposal.created_at.desc()).limit(100)).all()
    return [output(p) for p in rows]
@router.get('/proposals/{proposal_id}/audit')
def audit(proposal_id:str, db:Session=Depends(get_db),user:User=Depends(current_user)):
    if db.get(SoarProposal,proposal_id) is None:raise HTTPException(404,'Proposal not found')
    rows=db.scalars(select(SoarAudit).where(SoarAudit.proposal_id==proposal_id).order_by(SoarAudit.created_at)).all()
    return [{'action':r.action,'detail':r.detail,'created_at':r.created_at,'actor_id':r.actor_id} for r in rows]
@router.post('/proposals', status_code=201)
def propose(body:ProposalIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*PROPOSERS))):
    if body.playbook_key not in PLAYBOOKS:raise HTTPException(422,'Unsupported playbook')
    if body.incident_id and db.get(IncidentCase,body.incident_id) is None:raise HTTPException(404,'Incident not found')
    if body.correlation_id and db.get(CorrelationCase,body.correlation_id) is None:raise HTTPException(404,'Correlation not found')
    p=SoarProposal(playbook_key=body.playbook_key,incident_id=body.incident_id,correlation_id=body.correlation_id,
                   justification=body.justification.strip(),proposed_by=user.id,status='pending')
    db.add(p);db.flush();record(db,p,user,'proposed');db.commit();db.refresh(p);return output(p)
@router.post('/proposals/{proposal_id}/approve')
def approve(proposal_id:str,body:DecisionIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*APPROVERS))):
    p=db.get(SoarProposal,proposal_id)
    if p is None:raise HTTPException(404,'Proposal not found')
    if p.status!='pending':raise HTTPException(409,'Proposal is no longer pending')
    if p.proposed_by==user.id:raise HTTPException(403,'A different authorized approver is required')
    p.status='approved';p.approved_by=user.id;p.decided_at=datetime.now(timezone.utc);p.decision_note=body.note.strip()
    record(db,p,user,'approved',body.note.strip());db.commit();db.refresh(p);return output(p)
@router.post('/proposals/{proposal_id}/reject')
def reject(proposal_id:str,body:DecisionIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*APPROVERS))):
    p=db.get(SoarProposal,proposal_id)
    if p is None:raise HTTPException(404,'Proposal not found')
    if p.status!='pending':raise HTTPException(409,'Proposal is no longer pending')
    if p.proposed_by==user.id:raise HTTPException(403,'A different authorized reviewer is required')
    p.status='rejected';p.approved_by=user.id;p.decided_at=datetime.now(timezone.utc);p.decision_note=body.note.strip()
    record(db,p,user,'rejected',body.note.strip());db.commit();db.refresh(p);return output(p)
@router.post('/proposals/{proposal_id}/simulate')
def execute_simulation(proposal_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles(*APPROVERS))):
    p=db.get(SoarProposal,proposal_id)
    if p is None:raise HTTPException(404,'Proposal not found')
    if p.status!='approved':raise HTTPException(409,'Only approved proposals can be simulated')
    if p.approved_by is None:raise HTTPException(409,'Missing approval')
    p.output_json=simulate(p.playbook_key,p.justification);p.status='simulated';p.executed_at=datetime.now(timezone.utc)
    record(db,p,user,'simulated','Dry-run only, zero external actions');db.commit();db.refresh(p);return output(p)
