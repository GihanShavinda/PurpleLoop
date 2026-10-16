"""P15 explicit/limited CPU anomaly analyses; immutable results, no background activity."""
from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import Asset, User, TelemetryEvent, AuditLog, AnomalyAnalysisRun, AnomalyObservation
from .engine import bucketize, evaluate_buckets

router=APIRouter(prefix='/anomaly',tags=['P15 Anomaly Detection'])
WRITERS=('Administrator','Purple Team Engineer')

class RunRequest(BaseModel):
    asset_id: str
    lookback_hours: int = Field(default=6,ge=1,le=24)
    bucket_minutes: int = Field(default=15,ge=5,le=60)
    contamination: float = Field(default=0.08,ge=0.01,le=0.2)

def serialize_run(r):
    return {'id':r.id,'asset_id':r.asset_id,'created_at':r.created_at,'window_start':r.window_start,
            'window_end':r.window_end,'event_count':r.event_count,'bucket_count':r.bucket_count,
            'anomaly_count':r.anomaly_count,'bucket_minutes':r.bucket_minutes,'status':r.status,
            'parameters':r.parameters_json}

@router.get('/assets')
def assets(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [{'id':a.id,'name':a.hostname} for a in db.scalars(select(Asset).order_by(Asset.hostname).limit(100)).all()]

@router.get('/runs')
def runs(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [serialize_run(r) for r in db.scalars(select(AnomalyAnalysisRun).order_by(AnomalyAnalysisRun.created_at.desc()).limit(50)).all()]

@router.get('/runs/{run_id}/observations')
def observations(run_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    try: UUID(run_id)
    except ValueError: raise HTTPException(422,'Invalid run id')
    if db.get(AnomalyAnalysisRun,run_id) is None: raise HTTPException(404,'Run not found')
    rows=db.scalars(select(AnomalyObservation).where(AnomalyObservation.run_id==run_id).order_by(AnomalyObservation.bucket_start).limit(100)).all()
    return [{'id':r.id,'bucket_start':r.bucket_start,'anomaly_score':r.anomaly_score,
             'event_count':r.event_count,'explanation':r.explanation_json} for r in rows]

@router.post('/run',status_code=201)
def create_run(body:RunRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    try: UUID(body.asset_id)
    except ValueError: raise HTTPException(422,'Invalid asset id')
    if db.get(Asset,body.asset_id) is None: raise HTTPException(404,'Asset not found')
    if body.lookback_hours*60//body.bucket_minutes < 12: raise HTTPException(422,'At least 12 buckets required')
    end=datetime.now(timezone.utc).replace(second=0,microsecond=0)
    start=end-timedelta(hours=body.lookback_hours)
    # Explicit hard caps, latest 5000 ordered records, bounded 24 hours and one asset.
    rows=db.execute(select(TelemetryEvent.event_time,TelemetryEvent.event_type,TelemetryEvent.severity)
                    .where(TelemetryEvent.asset_id==body.asset_id,
                           TelemetryEvent.event_time>=start,TelemetryEvent.event_time<end)
                    .order_by(TelemetryEvent.event_time.desc()).limit(5001)).all()
    if len(rows)>5000:raise HTTPException(422,'Too many events (limit 5000); select a shorter lookback')
    if len(rows)<30:raise HTTPException(422,'At least 30 telemetry events required for a meaningful baseline')
    bins=bucketize(rows,start,end,body.bucket_minutes)
    try: alerts=evaluate_buckets(bins,body.contamination)
    except (ValueError,RuntimeError) as exc: raise HTTPException(422,str(exc))
    result=AnomalyAnalysisRun(asset_id=body.asset_id,initiated_by=user.id,window_start=start,
        window_end=end,bucket_minutes=body.bucket_minutes,event_count=len(rows),bucket_count=len(bins),
        anomaly_count=len(alerts),parameters_json={'model':'IsolationForest','n_estimators':100,'random_state':42,
            'contamination':body.contamination,'features':['volume','warnings','errors','distinct_types'],
            'sampling':'complete only up to 5000 events; no silent truncation'})
    db.add(result);db.flush()
    for observation in alerts:
        db.add(AnomalyObservation(run_id=result.id,bucket_start=observation['bucket_start'],
            anomaly_score=observation['anomaly_score'],event_count=observation['event_count'],
            explanation_json=observation['explanation']))
    db.add(AuditLog(actor_id=user.id,action='p15_anomaly_run',resource='anomaly_analysis_run',resource_id=result.id))
    db.commit();db.refresh(result)
    return serialize_run(result)
