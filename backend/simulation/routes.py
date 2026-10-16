"""Manual telemetry validation only; never executes commands or accesses VMware APIs."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import User, Asset, TelemetryEvent, LabSimulationRun, AuditLog
from .scenarios import SCENARIOS, render_command

router = APIRouter(prefix='/simulation',tags=['P13 Manual Lab Simulation'])
WRITERS = ('Administrator','Purple Team Engineer')

class StartBody(BaseModel):
    asset_id: str
    scenario_key: str = 'ubuntu_journal_marker'

class EndBody(BaseModel):
    note: str = Field(min_length=10,max_length=1000)

def output(r):
    return {'id':r.id,'asset_id':r.asset_id,'scenario_key':r.scenario_key,
            'marker':r.marker,'status':r.status,'started_at':r.started_at,
            'ended_at':r.ended_at,'evidence_event_id':r.evidence_event_id,
            'note':r.note,'command': render_command(r.scenario_key,r.marker)}

def add_audit(db,actor,action,rid):
    db.add(AuditLog(actor_id=actor.id,action=action,resource='lab_simulation_run',resource_id=rid))

@router.get('/scenarios')
def scenarios(user:User=Depends(current_user)):
    return [{'key':k,**v} for k,v in SCENARIOS.items()]

@router.get('/runs')
def list_runs(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(LabSimulationRun).order_by(LabSimulationRun.started_at.desc()).limit(100)).all()
    return [output(r) for r in rows]

@router.post('/runs',status_code=201)
def start(body:StartBody,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    if body.scenario_key not in SCENARIOS:raise HTTPException(422,'Scenario is not allowlisted')
    asset=db.get(Asset,body.asset_id)
    if not asset:raise HTTPException(404,'Asset not found')
    if asset.environment!='lab':raise HTTPException(422,'Only lab assets permitted')
    if 'ubuntu' not in ((asset.operating_system or '')+' '+asset.hostname).lower():
        raise HTTPException(422,'Scenario requires an Ubuntu asset')
    marker='PF13-'+uuid4().hex
    r=LabSimulationRun(asset_id=asset.id,scenario_key=body.scenario_key,marker=marker,
                       status='awaiting_evidence',initiated_by=user.id)
    db.add(r);db.flush();add_audit(db,user,'p13_started',r.id);db.commit();db.refresh(r)
    return output(r)

@router.post('/runs/{run_id}/verify')
def verify(run_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    r=db.get(LabSimulationRun,run_id)
    if not r:raise HTTPException(404,'Run not found')
    if r.status!='awaiting_evidence':raise HTTPException(409,'Run is already finalized')
    now=datetime.now(timezone.utc)
    if now-r.started_at.replace(tzinfo=r.started_at.tzinfo or timezone.utc)>timedelta(hours=2):
        r.status='expired';r.ended_at=now;add_audit(db,user,'p13_expired',r.id);db.commit();db.refresh(r);return output(r)
    event=db.scalar(select(TelemetryEvent).where(
        TelemetryEvent.asset_id==r.asset_id,
        TelemetryEvent.event_type.in_(("linux.journal", "linux_journal")),
        TelemetryEvent.received_at>=r.started_at,
        TelemetryEvent.message.contains(r.marker)
    ).order_by(TelemetryEvent.received_at.asc()).limit(1))
    if event is None:raise HTTPException(409,'Marker not observed in ingested Ubuntu journal telemetry yet')
    r.status='verified';r.ended_at=now;r.evidence_event_id=event.id
    add_audit(db,user,'p13_verified',r.id);db.commit();db.refresh(r)
    return output(r)

@router.post('/runs/{run_id}/close')
def close(run_id:str,body:EndBody,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    r=db.get(LabSimulationRun,run_id)
    if not r:raise HTTPException(404,'Run not found')
    if r.status!='awaiting_evidence':raise HTTPException(409,'Only pending runs can be closed')
    r.status='inconclusive';r.note=body.note.strip();r.ended_at=datetime.now(timezone.utc)
    add_audit(db,user,'p13_closed',r.id);db.commit();db.refresh(r);return output(r)
