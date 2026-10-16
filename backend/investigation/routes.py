"""P16 bounded investigations. No live model calls, no arbitrary SQL or execution."""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import (Asset, User, AuditLog, AnomalyAnalysisRun, AnomalyObservation,
                      CorrelationCase, InvestigationDraft)
from .composer import compose

router = APIRouter(prefix='/investigation', tags=['P16 Evidence-Grounded Investigation'])
WRITERS = ('Administrator', 'Purple Team Engineer')

def valid_uuid(value: str):
    try: UUID(value)
    except ValueError: raise HTTPException(422, 'Invalid identifier')

def export(d: InvestigationDraft) -> dict:
    return {'id':d.id, 'asset_id':d.asset_id, 'anomaly_run_id':d.anomaly_run_id,
            'correlation_id':d.correlation_id, 'status':d.status, 'created_at':d.created_at,
            'report':d.report_json, 'review_note':d.review_note, 'reviewed_at':d.reviewed_at}

class DraftRequest(BaseModel):
    anomaly_run_id: str
    correlation_id: str | None = None

class ReviewRequest(BaseModel):
    decision: str
    note: str = Field(min_length=10, max_length=2000)

@router.get('/sources')
def sources(db:Session=Depends(get_db),user:User=Depends(current_user)):
    runs=db.scalars(select(AnomalyAnalysisRun).order_by(AnomalyAnalysisRun.created_at.desc()).limit(50)).all()
    cases=db.scalars(select(CorrelationCase).order_by(CorrelationCase.created_at.desc()).limit(50)).all()
    ids={r.asset_id for r in runs} | {c.asset_id for c in cases}
    assets={a.id:a.hostname for a in db.scalars(select(Asset).where(Asset.id.in_(ids))).all()} if ids else {}
    return {'runs':[{'id':r.id,'asset_id':r.asset_id,'asset':assets.get(r.asset_id,r.asset_id),
                    'created_at':r.created_at,'anomaly_count':r.anomaly_count} for r in runs],
            'correlations':[{'id':c.id,'asset_id':c.asset_id,'asset':assets.get(c.asset_id,c.asset_id),
                             'risk_score':c.risk_score} for c in cases]}

@router.get('/drafts')
def drafts(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [export(d) for d in db.scalars(select(InvestigationDraft).order_by(InvestigationDraft.created_at.desc()).limit(50)).all()]

@router.post('/drafts',status_code=201)
def create(body:DraftRequest, db:Session=Depends(get_db), user:User=Depends(require_roles(*WRITERS))):
    valid_uuid(body.anomaly_run_id)
    run=db.get(AnomalyAnalysisRun,body.anomaly_run_id)
    if not run or run.status!='completed': raise HTTPException(404,'Completed anomaly run not found')
    corr=None
    if body.correlation_id:
        valid_uuid(body.correlation_id)
        corr=db.get(CorrelationCase,body.correlation_id)
        if not corr: raise HTTPException(404,'Correlation not found')
        if corr.asset_id!=run.asset_id: raise HTTPException(422,'Correlation must belong to the same asset')
    asset=db.get(Asset,run.asset_id)
    if not asset: raise HTTPException(404,'Asset not found')
    rows=db.scalars(select(AnomalyObservation).where(AnomalyObservation.run_id==run.id)
                    .order_by(AnomalyObservation.bucket_start).limit(26)).all()
    if len(rows)>25: raise HTTPException(422,'More than 25 outlier records; reduce source scope')
    observations=[{'id':x.id,'run_id':x.run_id,'bucket_start':x.bucket_start.isoformat(),
                   'event_count':x.event_count,'anomaly_score':x.anomaly_score} for x in rows]
    context=({'id':corr.id,'risk_score':corr.risk_score,'finding_count':corr.finding_count,
              'indicator_count':corr.indicator_count} if corr else None)
    report=compose(asset.hostname, observations, context)
    draft=InvestigationDraft(asset_id=run.asset_id,anomaly_run_id=run.id,
                            correlation_id=corr.id if corr else None,created_by=user.id,report_json=report)
    db.add(draft);db.flush()
    db.add(AuditLog(actor_id=user.id,action='p16_draft_created',resource='investigation_draft',resource_id=draft.id))
    db.commit();db.refresh(draft)
    return export(draft)

@router.post('/drafts/{draft_id}/review')
def review(draft_id:str,body:ReviewRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    valid_uuid(draft_id)
    if body.decision not in ('accepted','rejected'): raise HTTPException(422,'Decision must be accepted or rejected')
    draft=db.get(InvestigationDraft,draft_id)
    if not draft: raise HTTPException(404,'Draft not found')
    if draft.status!='draft': raise HTTPException(409,'Draft already reviewed')
    draft.status=body.decision
    draft.review_note=body.note
    draft.reviewed_by=user.id
    draft.reviewed_at=datetime.now(timezone.utc)
    db.add(AuditLog(actor_id=user.id,action='p16_draft_'+body.decision,resource='investigation_draft',resource_id=draft.id))
    db.commit();db.refresh(draft)
    return export(draft)
