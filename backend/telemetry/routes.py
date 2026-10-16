"""P3 telemetry API: JWT for management, isolated collector key for ingestion."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import secrets
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Asset, TelemetrySource, TelemetryEvent, User, AuditLog
from ..auth.security import current_user, require_roles

router=APIRouter(tags=['telemetry'])
SOURCE_TYPES={'sysmon','windows_event','auditd','linux_journal','suricata','zeek','osquery','pcap','custom'}

class SourceCreate(BaseModel):
    asset_id: str
    name: str = Field(min_length=2,max_length=150)
    source_type: str
    @field_validator('source_type')
    @classmethod
    def check_type(cls,value):
        if value not in SOURCE_TYPES: raise ValueError('Unsupported source type')
        return value

class EventInput(BaseModel):
    event_time: datetime
    event_type: str = Field(min_length=1,max_length=120)
    severity: Literal['debug','info','low','medium','high','critical'] = 'info'
    message: str = Field(min_length=1,max_length=2048)
    payload: dict = Field(default_factory=dict)
    @field_validator('event_time')
    @classmethod
    def valid_timestamp(cls,value):
        if value.tzinfo is None: raise ValueError('Timestamp must include a timezone')
        if value > datetime.now(timezone.utc)+timedelta(minutes=5): raise ValueError('Timestamp is in the future')
        return value

class BatchInput(BaseModel):
    events: list[EventInput] = Field(min_length=1,max_length=100)

def present(source):
    if not source.last_seen_at: state='configured' if source.enabled else 'disabled'
    elif source.last_seen_at < datetime.now(timezone.utc)-timedelta(minutes=10): state='stale' if source.enabled else 'disabled'
    else: state='receiving' if source.enabled else 'disabled'
    return {'id':source.id,'asset_id':source.asset_id,'name':source.name,'source_type':source.source_type,'enabled':source.enabled,'last_seen_at':source.last_seen_at,'state':state}

@router.post('/telemetry/sources',status_code=201)
def create_source(body:SourceCreate,db:Session=Depends(get_db),actor:User=Depends(require_roles('Administrator','Purple Team Engineer'))):
    if not db.get(Asset,body.asset_id): raise HTTPException(404,'Asset not found')
    key=secrets.token_urlsafe(48)
    source=TelemetrySource(asset_id=body.asset_id,name=body.name,source_type=body.source_type,enabled=True,token_sha256=sha256(key.encode()).hexdigest())
    db.add(source);db.flush()
    db.add(AuditLog(actor_id=actor.id,action='created',resource='telemetry_source',resource_id=source.id))
    db.commit();db.refresh(source)
    return {'source':present(source),'collector_key':key,'warning':'Save the collector key now. It will not be displayed again.'}

@router.get('/telemetry/sources')
def list_sources(asset_id:str|None=None,db:Session=Depends(get_db),actor:User=Depends(current_user)):
    query=select(TelemetrySource).order_by(TelemetrySource.created_at.desc().nullslast(),TelemetrySource.id)
    if asset_id: query=query.where(TelemetrySource.asset_id==asset_id)
    return [present(s) for s in db.scalars(query.limit(300)).all()]

@router.patch('/telemetry/sources/{source_id}')
def switch_source(source_id:str,enabled:bool,db:Session=Depends(get_db),actor:User=Depends(require_roles('Administrator','Purple Team Engineer'))):
    source=db.get(TelemetrySource,source_id)
    if not source:raise HTTPException(404,'Source not found')
    source.enabled=enabled
    db.add(AuditLog(actor_id=actor.id,action='enabled' if enabled else 'disabled',resource='telemetry_source',resource_id=source.id))
    db.commit();db.refresh(source)
    return present(source)

@router.post('/telemetry/ingest',status_code=202)
def ingest(batch:BatchInput,x_collector_key:str|None=Header(default=None),db:Session=Depends(get_db)):
    if not x_collector_key or len(x_collector_key)>256:raise HTTPException(401,'Collector authentication required')
    source=db.scalar(select(TelemetrySource).where(TelemetrySource.token_sha256==sha256(x_collector_key.encode()).hexdigest()))
    if not source or not source.enabled:raise HTTPException(401,'Invalid or disabled collector')
    if not db.get(Asset,source.asset_id):raise HTTPException(409,'Source asset missing')
    # Bounded batches, payload size enforced via JSON byte length.
    import json
    if len(json.dumps(batch.model_dump(mode='json')).encode('utf-8'))>256_000:raise HTTPException(413,'Batch too large')
    for e in batch.events:
        db.add(TelemetryEvent(source_id=source.id,asset_id=source.asset_id,event_time=e.event_time,event_type=e.event_type,severity=e.severity,message=e.message,payload=e.payload))
    source.last_seen_at=datetime.now(timezone.utc)
    db.commit()
    return {'accepted':len(batch.events),'source_id':source.id}

@router.get('/telemetry/events')
def events(asset_id:str|None=None,source_id:str|None=None,severity:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),db:Session=Depends(get_db),actor:User=Depends(current_user)):
    q=select(TelemetryEvent)
    if asset_id:q=q.where(TelemetryEvent.asset_id==asset_id)
    if source_id:q=q.where(TelemetryEvent.source_id==source_id)
    if severity:q=q.where(TelemetryEvent.severity==severity)
    rows=db.scalars(q.order_by(TelemetryEvent.received_at.desc(),TelemetryEvent.id.desc()).offset(offset).limit(limit)).all()
    return [{'id':e.id,'source_id':e.source_id,'asset_id':e.asset_id,'event_time':e.event_time,'received_at':e.received_at,'event_type':e.event_type,'severity':e.severity,'message':e.message,'payload':e.payload} for e in rows]

@router.get('/telemetry/summary')
def summary(db:Session=Depends(get_db),actor:User=Depends(current_user)):
    sources=db.scalars(select(TelemetrySource)).all()
    return {'sources':len(sources),'receiving':sum(present(s)['state']=='receiving' for s in sources),'events':db.scalar(select(func.count(TelemetryEvent.id))) or 0}
