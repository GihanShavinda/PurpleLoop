from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (ValidationScenario, ValidationRun, ValidationEvidence, DetectionRule,
                      DetectionFinding, TelemetryEvent, Asset, AuditLog, User)
from ..auth.security import current_user, require_roles
from .coverage import valid_technique, outcome, coverage_stats

router=APIRouter(prefix='/validation', tags=['P5 validation'])
WRITERS=('Administrator','Purple Team Engineer','Detection Engineer')

class ScenarioIn(BaseModel):
    name:str=Field(min_length=3,max_length=160)
    description:str=Field(default='',max_length=1000)
    rule_id:str
    asset_id:str
    technique_id:str
    instructions:str=Field(min_length=8,max_length=3000)
    @field_validator('technique_id')
    @classmethod
    def technique(cls,v):
        if not valid_technique(v): raise ValueError('Use ATT&CK technique ID like T1059 or T1059.001')
        return v

def scenario_out(s):
    return {k:getattr(s,k) for k in ('id','name','description','rule_id','asset_id','technique_id','instructions','enabled','created_at')}

def run_out(r):
    return {k:getattr(r,k) for k in ('id','scenario_id','started_by','started_at','finished_at','status','notes','evidence_count')}

@router.get('/scenarios')
def scenarios(db:Session=Depends(get_db), actor:User=Depends(current_user)):
    return [scenario_out(s) for s in db.scalars(select(ValidationScenario).order_by(ValidationScenario.created_at.desc()).limit(300)).all()]

@router.post('/scenarios',status_code=201)
def create(body:ScenarioIn,db:Session=Depends(get_db),actor:User=Depends(require_roles(*WRITERS))):
    if not db.get(DetectionRule,body.rule_id): raise HTTPException(422,'Unknown detection rule')
    if not db.get(Asset,body.asset_id): raise HTTPException(422,'Unknown asset')
    if db.scalar(select(ValidationScenario.id).where(ValidationScenario.name==body.name)):
        raise HTTPException(409,'Scenario name already exists')
    scenario=ValidationScenario(**body.model_dump())
    db.add(scenario);db.flush()
    db.add(AuditLog(actor_id=actor.id,action='created',resource='validation_scenario',resource_id=scenario.id))
    db.commit();db.refresh(scenario)
    return scenario_out(scenario)

@router.post('/scenarios/{scenario_id}/start',status_code=201)
def start(scenario_id:str,db:Session=Depends(get_db),actor:User=Depends(require_roles(*WRITERS))):
    s=db.get(ValidationScenario,scenario_id)
    if not s or not s.enabled:raise HTTPException(404,'Enabled scenario not found')
    running=db.scalar(select(ValidationRun.id).where(ValidationRun.scenario_id==scenario_id,ValidationRun.status=='running'))
    if running:raise HTTPException(409,'Scenario has a running validation')
    run=ValidationRun(scenario_id=s.id,started_by=actor.id,started_at=datetime.now(timezone.utc))
    db.add(run);db.flush()
    db.add(AuditLog(actor_id=actor.id,action='started',resource='validation_run',resource_id=run.id))
    db.commit();db.refresh(run)
    return run_out(run)

class FinishIn(BaseModel):
    test_performed:bool=True
    notes:str=Field(default='',max_length=2000)

@router.post('/runs/{run_id}/finish')
def finish(run_id:str,body:FinishIn,db:Session=Depends(get_db),actor:User=Depends(require_roles(*WRITERS))):
    run=db.get(ValidationRun,run_id)
    if not run:raise HTTPException(404,'Run not found')
    if run.status!='running':raise HTTPException(409,'Run already finished')
    scenario=db.get(ValidationScenario,run.scenario_id)
    ended=datetime.now(timezone.utc)
    # Only link actual P4 findings on the expected rule+asset, whose underlying event
    # occurred during the validation window. Do not invent success from an instruction.
    rows=db.execute(select(DetectionFinding.id).join(TelemetryEvent,DetectionFinding.event_id==TelemetryEvent.id)
        .where(DetectionFinding.rule_id==scenario.rule_id,DetectionFinding.asset_id==scenario.asset_id,
               TelemetryEvent.event_time>=run.started_at,TelemetryEvent.event_time<=ended)
        .order_by(DetectionFinding.created_at.desc()).limit(200)).all()
    ids=[x[0] for x in rows]
    for fid in ids:db.add(ValidationEvidence(run_id=run.id,finding_id=fid))
    run.evidence_count=len(ids)
    run.status=outcome(ids,body.test_performed)
    run.notes=body.notes
    run.finished_at=ended
    db.add(AuditLog(actor_id=actor.id,action='finished',resource='validation_run',resource_id=run.id))
    db.commit();db.refresh(run)
    return run_out(run)

@router.get('/runs')
def runs(limit:int=Query(100,ge=1,le=200),db:Session=Depends(get_db),actor:User=Depends(current_user)):
    return [run_out(r) for r in db.scalars(select(ValidationRun).order_by(ValidationRun.started_at.desc()).limit(limit)).all()]

@router.get('/runs/{run_id}/evidence')
def evidence(run_id:str,db:Session=Depends(get_db),actor:User=Depends(current_user)):
    if not db.get(ValidationRun,run_id):raise HTTPException(404,'Run not found')
    rows=db.execute(select(ValidationEvidence.finding_id,DetectionFinding.event_id,TelemetryEvent.event_type,TelemetryEvent.message)
      .join(DetectionFinding,ValidationEvidence.finding_id==DetectionFinding.id)
      .join(TelemetryEvent,TelemetryEvent.id==DetectionFinding.event_id)
      .where(ValidationEvidence.run_id==run_id).limit(200)).all()
    return [{'finding_id':fid,'event_id':eid,'event_type':etype,'message':msg} for fid,eid,etype,msg in rows]

@router.get('/summary')
def summary(db:Session=Depends(get_db),actor:User=Depends(current_user)):
    ss=list(db.scalars(select(ValidationScenario).limit(1000)).all())
    runs=list(db.scalars(select(ValidationRun).order_by(ValidationRun.started_at.desc()).limit(3000)).all())
    latest={}
    for r in runs:
        if r.scenario_id not in latest:latest[r.scenario_id]=r
    result=coverage_stats(ss,list(latest.values()))
    result['runs']=len(runs)
    result['techniques_with_scenarios']=len({s.technique_id for s in ss if s.enabled})
    result['methodology']='Scenario-based observed detections; not comprehensive ATT&CK coverage'
    return result
