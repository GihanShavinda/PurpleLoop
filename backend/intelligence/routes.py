"""P8 manual intelligence and bounded retrospective enrichment. No outbound IOC checks."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import IntelligenceIndicator, IntelligenceMatch, TelemetryEvent, AuditLog, User
from ..auth.security import current_user, require_roles
from .matching import canonical, event_contains

router=APIRouter(prefix='/intelligence', tags=['P8 threat intelligence'])
WRITERS=('Administrator','Purple Team Engineer','SOC Analyst','Detection Engineer')

def indicator_data(x):
    return {'id':x.id,'kind':x.kind,'value':x.value,'source_label':x.source_label,'confidence':x.confidence,'description':x.description,'enabled':x.enabled,'created_at':x.created_at}

class NewIndicator(BaseModel):
    kind: str
    value: str=Field(min_length=2,max_length=255)
    source_label: str=Field(default='manual',min_length=2,max_length=160)
    confidence: int=Field(default=50,ge=0,le=100)
    description: str=Field(default='',max_length=1000)

@router.get('/indicators')
def indicators(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(IntelligenceIndicator).order_by(IntelligenceIndicator.created_at.desc()).limit(200)).all()
    return [indicator_data(x) for x in rows]

@router.post('/indicators',status_code=201)
def create(body:NewIndicator,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    try:value=canonical(body.kind,body.value)
    except ValueError as e:raise HTTPException(422,str(e)) from e
    item=IntelligenceIndicator(kind=body.kind,value=value,source_label=body.source_label,confidence=body.confidence,description=body.description,created_by=user.id)
    db.add(item)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Indicator already registered')
    db.refresh(item)
    return indicator_data(item)

@router.patch('/indicators/{indicator_id}')
def toggle(indicator_id:str,enabled:bool,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    item=db.get(IntelligenceIndicator,indicator_id)
    if not item:raise HTTPException(404,'Indicator not found')
    item.enabled=enabled
    db.add(AuditLog(actor_id=user.id,action='p8_indicator_toggle',resource='intelligence_indicator',resource_id=item.id))
    db.commit();db.refresh(item)
    return indicator_data(item)

class EnrichmentRequest(BaseModel):
    lookback_hours:int=Field(default=1,ge=1,le=168)
    max_events:int=Field(default=500,ge=1,le=1000)

@router.post('/enrich')
def enrich(body:EnrichmentRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    """Explicit single bounded request. No cron, polling, or external HTTP."""
    cutoff=datetime.now(timezone.utc)-timedelta(hours=body.lookback_hours)
    indicators=db.scalars(select(IntelligenceIndicator).where(IntelligenceIndicator.enabled.is_(True)).order_by(IntelligenceIndicator.created_at.desc()).limit(100)).all()
    events=db.scalars(select(TelemetryEvent).where(TelemetryEvent.event_time>=cutoff).order_by(TelemetryEvent.event_time.desc()).limit(body.max_events)).all()
    new=0
    for ev in events:
        for ind in indicators:
            if not event_contains(ind.kind,ind.value,ev.message,ev.payload):continue
            exists=db.scalar(select(IntelligenceMatch.id).where(IntelligenceMatch.indicator_id==ind.id,IntelligenceMatch.event_id==ev.id))
            if exists:continue
            db.add(IntelligenceMatch(indicator_id=ind.id,event_id=ev.id,asset_id=ev.asset_id));new+=1
    db.add(AuditLog(actor_id=user.id,action='p8_enrich',resource='intelligence',resource_id=None))
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Concurrent enrichment conflict: retry')
    return {'indicators_checked':len(indicators),'events_checked':len(events),'new_matches':new}

@router.get('/matches')
def matches(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.execute(select(IntelligenceMatch,IntelligenceIndicator,TelemetryEvent).join(IntelligenceIndicator,IntelligenceMatch.indicator_id==IntelligenceIndicator.id).join(TelemetryEvent,IntelligenceMatch.event_id==TelemetryEvent.id).order_by(IntelligenceMatch.created_at.desc()).limit(100)).all()
    return [{'id':m.id,'indicator_id':i.id,'indicator':i.value,'kind':i.kind,'asset_id':m.asset_id,'event_id':e.id,'event_time':e.event_time,'event_type':e.event_type,'message':e.message[:400]} for m,i,e in rows]

@router.get('/summary')
def summary(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return {'indicators':db.scalar(select(func.count()).select_from(IntelligenceIndicator)), 'enabled':db.scalar(select(func.count()).select_from(IntelligenceIndicator).where(IntelligenceIndicator.enabled.is_(True))),'matches':db.scalar(select(func.count()).select_from(IntelligenceMatch))}
