"""On-demand, exact-evidence P13->P4 detection assessment."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import User, AuditLog, DetectionRule, DetectionFinding, LabSimulationRun, DetectionCoverageAssessment
from .logic import result_for, summarize

router=APIRouter(prefix='/coverage',tags=['P14 Detection Coverage'])
WRITERS=('Administrator','Purple Team Engineer')

class AssessBody(BaseModel):
    simulation_run_id:str
    rule_id:str

def serialize(a):
    return {'id':a.id,'simulation_run_id':a.simulation_run_id,'rule_id':a.rule_id,
            'event_id':a.event_id,'finding_id':a.finding_id,'outcome':a.outcome,
            'explanation':a.explanation,'assessed_by':a.assessed_by,'assessed_at':a.assessed_at}

@router.get('/runs')
def runs(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(LabSimulationRun).where(LabSimulationRun.status=='verified')
                    .order_by(LabSimulationRun.started_at.desc()).limit(100)).all()
    return [{'id':r.id,'asset_id':r.asset_id,'marker':r.marker,'status':r.status,
             'event_id':r.evidence_event_id,'started_at':r.started_at} for r in rows]

@router.get('/rules')
def rules(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(DetectionRule).order_by(DetectionRule.name).limit(200)).all()
    return [{'id':r.id,'name':r.name,'enabled':r.enabled,'event_type':r.event_type} for r in rows]

@router.get('/assessments')
def assessments(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(DetectionCoverageAssessment).order_by(DetectionCoverageAssessment.assessed_at.desc()).limit(100)).all()
    return [serialize(a) for a in rows]

@router.get('/summary')
def summary(db:Session=Depends(get_db),user:User=Depends(current_user)):
    # Bounded dashboard, report its scope rather than claiming ATT&CK-wide coverage.
    outcomes=db.scalars(select(DetectionCoverageAssessment.outcome).order_by(DetectionCoverageAssessment.assessed_at.desc()).limit(1000)).all()
    return {**summarize(list(outcomes)),'scope':'latest 1000 assessments; operator-selected P13 runs and P4 rules'}

@router.post('/assess',status_code=201)
def assess(body:AssessBody,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    run=db.get(LabSimulationRun,body.simulation_run_id)
    if run is None:raise HTTPException(404,'P13 run not found')
    if run.status!='verified' or not run.evidence_event_id:
        raise HTTPException(409,'P13 run must have verified telemetry evidence')
    rule=db.get(DetectionRule,body.rule_id)
    if rule is None:raise HTTPException(404,'Detection rule not found')
    existing=db.scalar(select(DetectionCoverageAssessment).where(
        DetectionCoverageAssessment.simulation_run_id==run.id,
        DetectionCoverageAssessment.rule_id==rule.id))
    if existing is not None:return serialize(existing)
    finding=db.scalar(select(DetectionFinding).where(
        DetectionFinding.rule_id==rule.id,
        DetectionFinding.event_id==run.evidence_event_id,
        DetectionFinding.asset_id==run.asset_id).limit(1))
    outcome,explanation=result_for(True,finding is not None)
    a=DetectionCoverageAssessment(simulation_run_id=run.id,rule_id=rule.id,
        event_id=run.evidence_event_id,finding_id=finding.id if finding else None,
        outcome=outcome,explanation=explanation,assessed_by=user.id)
    db.add(a);db.flush()
    db.add(AuditLog(actor_id=user.id,action='p14_assessed',resource='detection_coverage_assessment',resource_id=a.id))
    db.commit();db.refresh(a)
    return serialize(a)
