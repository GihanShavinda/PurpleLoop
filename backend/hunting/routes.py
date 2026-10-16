"""P7 read-only bounded hunting plus explicit saved hunt and incident evidence actions."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import TelemetryEvent, Asset, TelemetrySource, SavedHunt, HuntEvidence, IncidentCase, User, AuditLog
from ..auth.security import current_user, require_roles
from .query import validate_window, escaped_contains, normalize_ioc

router=APIRouter(prefix='/hunting',tags=['P7 threat hunting'])
WRITERS=('Administrator','Purple Team Engineer','SOC Analyst','Detection Engineer')

def to_dict(ev):
    return {'id':ev.id,'asset_id':ev.asset_id,'source_id':ev.source_id,'event_time':ev.event_time,
            'event_type':ev.event_type,'severity':ev.severity,'message':ev.message[:1000],
            'payload':ev.payload}

class Filters(BaseModel):
    start: datetime
    end: datetime
    asset_id: str | None=None
    source_id: str | None=None
    event_type: str | None=Field(default=None,max_length=120)
    severity: str | None=Field(default=None,max_length=20)
    text: str | None=Field(default=None,max_length=160)
    limit: int=Field(default=100,ge=1,le=200)
    offset: int=Field(default=0,ge=0,le=10000)

def apply_filters(stmt, f:Filters):
    try: start,end=validate_window(f.start,f.end)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    stmt=stmt.where(TelemetryEvent.event_time>=start,TelemetryEvent.event_time<end)
    if f.asset_id: stmt=stmt.where(TelemetryEvent.asset_id==f.asset_id)
    if f.source_id: stmt=stmt.where(TelemetryEvent.source_id==f.source_id)
    if f.event_type: stmt=stmt.where(TelemetryEvent.event_type==f.event_type)
    if f.severity: stmt=stmt.where(TelemetryEvent.severity==f.severity)
    if f.text: stmt=stmt.where(TelemetryEvent.message.ilike(escaped_contains(f.text),escape=chr(92)))
    return stmt

@router.post('/search')
def search(f:Filters,db:Session=Depends(get_db),user:User=Depends(current_user)):
    stmt=apply_filters(select(TelemetryEvent),f)
    rows=db.scalars(stmt.order_by(TelemetryEvent.event_time.desc(),TelemetryEvent.id.desc()).offset(f.offset).limit(f.limit)).all()
    return {'events':[to_dict(x) for x in rows],'returned':len(rows),'limit':f.limit,'offset':f.offset,
            'has_more':len(rows)==f.limit}

class IOCQuery(BaseModel):
    kind:str
    value:str=Field(min_length=2,max_length=255)
    start:datetime
    end:datetime
    asset_id:str | None=None
    limit:int=Field(default=100,ge=1,le=100)

@router.post('/ioc')
def ioc(body:IOCQuery,db:Session=Depends(get_db),user:User=Depends(current_user)):
    try: value=normalize_ioc(body.kind,body.value)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    f=Filters(start=body.start,end=body.end,asset_id=body.asset_id,limit=body.limit)
    # Search only selected, documented normalized event fields and the free-text message.
    # JSON fields are accessed as text, never compiled into executable queries.
    keys={'ip':('src_ip','dest_ip','SourceIp','DestinationIp'),
          'domain':('QueryName','query','hostname'),
          'hash':('Hashes','hash','sha256'),
          'process':('Image','CommandLine','image','process_name')}[body.kind]
    pred=[TelemetryEvent.message.ilike(escaped_contains(value),escape=chr(92))]
    for key in keys:
        pred.append(TelemetryEvent.payload[key].as_string().ilike(escaped_contains(value),escape=chr(92)))
    stmt=apply_filters(select(TelemetryEvent),f).where(or_(*pred))
    rows=db.scalars(stmt.order_by(TelemetryEvent.event_time.desc()).limit(body.limit)).all()
    return {'kind':body.kind,'value':value,'events':[to_dict(x) for x in rows],'returned':len(rows)}

class SavedHuntIn(BaseModel):
    name:str=Field(min_length=3,max_length=160)
    filters:Filters

@router.get('/saved')
def saved(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(SavedHunt).where(SavedHunt.created_by==user.id).order_by(SavedHunt.created_at.desc()).limit(100)).all()
    return [{'id':h.id,'name':h.name,'filters':h.filters,'created_at':h.created_at} for h in rows]

@router.post('/saved',status_code=201)
def save(body:SavedHuntIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    try:validate_window(body.filters.start,body.filters.end)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    h=SavedHunt(name=body.name,filters=body.filters.model_dump(mode='json'),created_by=user.id)
    db.add(h);db.commit();db.refresh(h)
    return {'id':h.id,'name':h.name}

@router.delete('/saved/{hunt_id}',status_code=204)
def remove_saved(hunt_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    h=db.get(SavedHunt,hunt_id)
    if not h or h.created_by!=user.id:raise HTTPException(404,'Saved hunt not found')
    db.delete(h);db.commit()

class EvidenceIn(BaseModel):
    event_id:str
    note:str=Field(default='',max_length=500)

@router.post('/incidents/{case_id}/evidence',status_code=201)
def link_evidence(case_id:str,body:EvidenceIn,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    case=db.get(IncidentCase,case_id); event=db.get(TelemetryEvent,body.event_id)
    if case is None or event is None:raise HTTPException(404,'Case or event not found')
    if case.asset_id!=event.asset_id:raise HTTPException(422,'Evidence must belong to incident asset')
    if case.status in ('resolved','false_positive'):raise HTTPException(409,'Case is closed')
    record=HuntEvidence(case_id=case_id,event_id=event.id,actor_id=user.id,note=body.note)
    db.add(record);db.add(AuditLog(actor_id=user.id,action='linked_hunt_event',resource='incident_case',resource_id=case_id))
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Event already linked to incident')
    return {'id':record.id,'case_id':case_id,'event_id':event.id}

@router.get('/incidents/{case_id}/evidence')
def incident_evidence(case_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if db.get(IncidentCase,case_id) is None:raise HTTPException(404,'Case not found')
    rows=db.execute(select(HuntEvidence,TelemetryEvent).join(TelemetryEvent,HuntEvidence.event_id==TelemetryEvent.id)
        .where(HuntEvidence.case_id==case_id).order_by(HuntEvidence.created_at.desc()).limit(100)).all()
    return [{'id':link.id,'note':link.note,'linked_at':link.created_at,'event':to_dict(ev)} for link,ev in rows]
