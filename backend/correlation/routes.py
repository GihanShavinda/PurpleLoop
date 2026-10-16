"""P9 bounded, manually triggered correlation. No automatic response or scans."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import (Asset, TelemetryEvent, DetectionFinding, IntelligenceMatch,
                      IntelligenceIndicator, CorrelationCase, CorrelationEvidence, AuditLog, User)
from .scoring import score

router=APIRouter(prefix='/correlation',tags=['P9 correlation'])
WRITERS=('Administrator','Purple Team Engineer','SOC Analyst','Detection Engineer')

class EvaluateRequest(BaseModel):
    asset_id:str=Field(min_length=36,max_length=36)
    window_minutes:int=Field(default=60,ge=5,le=240)
    max_evidence:int=Field(default=100,ge=2,le=200)

class ReviewRequest(BaseModel):
    status:str


def case_data(c):
    return {'id':c.id,'asset_id':c.asset_id,'window_start':c.window_start,
      'window_end':c.window_end,'risk_score':c.risk_score,'risk_reasons':c.risk_reasons,
      'finding_count':c.finding_count,'indicator_count':c.indicator_count,
      'status':c.status,'created_at':c.created_at}

@router.post('/evaluate')
def evaluate(body:EvaluateRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    asset=db.get(Asset,body.asset_id)
    if asset is None: raise HTTPException(404,'Asset not found')
    # UTC whole-minute bounds make repeated evaluations idempotent within each minute.
    end=datetime.now(timezone.utc).replace(second=0,microsecond=0)
    start=end-timedelta(minutes=body.window_minutes)
    recent=db.scalar(select(CorrelationCase).where(CorrelationCase.asset_id==asset.id,
        CorrelationCase.window_start==start,CorrelationCase.window_end==end))
    if recent is not None: return {'created':False,'case':case_data(recent)}
    rows=db.execute(select(DetectionFinding,TelemetryEvent).join(TelemetryEvent,DetectionFinding.event_id==TelemetryEvent.id)
       .where(DetectionFinding.asset_id==asset.id,TelemetryEvent.event_time>=start,TelemetryEvent.event_time<=end)
       .order_by(TelemetryEvent.event_time.desc()).limit(body.max_evidence)).all()
    intelligence=db.execute(select(IntelligenceMatch,IntelligenceIndicator,TelemetryEvent)
       .join(IntelligenceIndicator,IntelligenceMatch.indicator_id==IntelligenceIndicator.id)
       .join(TelemetryEvent,IntelligenceMatch.event_id==TelemetryEvent.id)
       .where(IntelligenceMatch.asset_id==asset.id,TelemetryEvent.event_time>=start,TelemetryEvent.event_time<=end)
       .order_by(TelemetryEvent.event_time.desc()).limit(body.max_evidence)).all()
    if not rows and not intelligence:
        return {'created':False,'reason':'No matching detection or intelligence evidence for this asset and window'}
    # One evidence link per event and kind. Store only bounded, observed evidence.
    seen=set(); find_evidence=[]; intel_evidence=[]
    for finding,event in rows:
        if event.id not in seen:
            find_evidence.append((finding,event));seen.add(event.id)
    seen.clear()
    for match,indicator,event in intelligence:
        if event.id not in seen:
            intel_evidence.append((match,indicator,event));seen.add(event.id)
    total=len(find_evidence)+len(intel_evidence)
    if total>body.max_evidence:
        combined=[('finding', f.id,ev.id,ev.event_time,f.severity,None) for f,ev in find_evidence]+[('intelligence',m.id,ev.id,ev.event_time,None,i.confidence) for m,i,ev in intel_evidence]
        combined.sort(key=lambda x:x[3],reverse=True)
        limited=combined[:body.max_evidence]
    else:
        limited=[('finding',f.id,ev.id,ev.event_time,f.severity,None) for f,ev in find_evidence]+[('intelligence',m.id,ev.id,ev.event_time,None,i.confidence) for m,i,ev in intel_evidence]
    finding_severities=[e[4] for e in limited if e[0]=='finding']
    intel_confidences=[e[5] for e in limited if e[0]=='intelligence']
    risk,reasons=score(finding_severities,intel_confidences,asset.criticality)
    case=CorrelationCase(asset_id=asset.id,window_start=start,window_end=end,risk_score=risk,
        risk_reasons=reasons,finding_count=len(finding_severities),indicator_count=len(intel_confidences),created_by=user.id)
    db.add(case);db.flush()
    for kind,source_id,event_id,_,_,_ in limited:
        db.add(CorrelationEvidence(correlation_id=case.id,event_id=event_id,evidence_kind=kind,
            finding_id=source_id if kind=='finding' else None,
            intelligence_match_id=source_id if kind=='intelligence' else None))
    db.add(AuditLog(actor_id=user.id,action='p9_correlation_evaluate',resource='correlation_case',resource_id=case.id))
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Concurrent correlation, please refresh')
    db.refresh(case)
    return {'created':True,'case':case_data(case)}

@router.get('/cases')
def cases(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(CorrelationCase).order_by(CorrelationCase.created_at.desc()).limit(100)).all()
    return [case_data(c) for c in rows]

@router.get('/cases/{case_id}/evidence')
def evidence(case_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    c=db.get(CorrelationCase,case_id)
    if c is None:raise HTTPException(404,'Correlation case not found')
    rows=db.execute(select(CorrelationEvidence,TelemetryEvent).join(TelemetryEvent,CorrelationEvidence.event_id==TelemetryEvent.id)
        .where(CorrelationEvidence.correlation_id==case_id).order_by(TelemetryEvent.event_time.asc()).limit(200)).all()
    return [{'id':e.id,'event_id':ev.id,'event_time':ev.event_time,'event_type':ev.event_type,'message':ev.message[:300],
      'kind':e.evidence_kind,'finding_id':e.finding_id,'intelligence_match_id':e.intelligence_match_id} for e,ev in rows]

@router.patch('/cases/{case_id}')
def review(case_id:str,body:ReviewRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    if body.status not in ('new','reviewed','dismissed'):
        raise HTTPException(422,'Unsupported review status')
    c=db.get(CorrelationCase,case_id)
    if c is None:raise HTTPException(404,'Correlation case not found')
    c.status=body.status
    db.add(AuditLog(actor_id=user.id,action='p9_correlation_review',resource='correlation_case',resource_id=c.id))
    db.commit();db.refresh(c)
    return case_data(c)
