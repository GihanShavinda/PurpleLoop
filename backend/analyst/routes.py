"""P10 on-demand, bounded analyst reports; no autonomous actions."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import (User, Asset, CorrelationCase, CorrelationEvidence,
                      TelemetryEvent, AnalystReport, AuditLog)
from .report import build_report, MAX_EVIDENCE

router = APIRouter(prefix='/analyst', tags=['P10 analyst'])
WRITERS=('Administrator','Purple Team Engineer','SOC Analyst','Detection Engineer')

class GenerateRequest(BaseModel):
    correlation_id: str = Field(min_length=36,max_length=36)

class ReviewRequest(BaseModel):
    status: str
    note: str = Field(default='',max_length=2000)

def serialized(report: AnalystReport) -> dict:
    return {'id':report.id,'correlation_id':report.correlation_id,
            'asset_id':report.asset_id,'status':report.status,'created_at':report.created_at,
            'reviewed_at':report.reviewed_at,'review_note':report.review_note,
            'generator_version':report.generator_version,'report':report.report_json}

@router.get('/reports')
def list_reports(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(AnalystReport).order_by(AnalystReport.created_at.desc()).limit(50)).all()
    return [serialized(r) for r in rows]

@router.get('/reports/{report_id}')
def get_report(report_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    r=db.get(AnalystReport,report_id)
    if r is None:raise HTTPException(404,'Report not found')
    return serialized(r)

@router.post('/generate',status_code=201)
def generate(body:GenerateRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    case=db.get(CorrelationCase,body.correlation_id)
    if case is None:raise HTTPException(404,'Correlation case not found')
    asset=db.get(Asset,case.asset_id)
    if asset is None:raise HTTPException(404,'Asset not found')
    rows=db.execute(select(CorrelationEvidence,TelemetryEvent)
        .join(TelemetryEvent,CorrelationEvidence.event_id==TelemetryEvent.id)
        .where(CorrelationEvidence.correlation_id==case.id)
        .order_by(TelemetryEvent.event_time.asc()).limit(MAX_EVIDENCE)).all()
    evidence=[{'event_id':ev.id,'timestamp':ev.event_time.isoformat(),
               'kind':link.evidence_kind,'event_type':ev.event_type,'message':ev.message}
              for link,ev in rows]
    snapshot=build_report({'asset_label':asset.hostname,'risk_score':case.risk_score},evidence)
    r=AnalystReport(correlation_id=case.id,asset_id=case.asset_id,
        created_by=user.id,report_json=snapshot,status='draft',generator_version='evidence-v1')
    db.add(r);db.flush()
    db.add(AuditLog(actor_id=user.id,action='p10_report_generate',resource='analyst_report',resource_id=r.id))
    db.commit();db.refresh(r)
    return serialized(r)

@router.patch('/reports/{report_id}/review')
def review(report_id:str,body:ReviewRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    if body.status not in ('accepted','rejected'):
        raise HTTPException(422,'Review status must be accepted or rejected')
    r=db.get(AnalystReport,report_id)
    if r is None:raise HTTPException(404,'Report not found')
    if r.status!='draft':raise HTTPException(409,'This report is already reviewed')
    if not body.note.strip():raise HTTPException(422,'A review note is required')
    r.status=body.status;r.review_note=body.note.strip();r.reviewed_by=user.id;r.reviewed_at=datetime.now(timezone.utc)
    db.add(AuditLog(actor_id=user.id,action='p10_report_review',resource='analyst_report',resource_id=r.id))
    db.commit();db.refresh(r)
    return serialized(r)
