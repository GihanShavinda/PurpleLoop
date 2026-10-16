from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DetectionRule, DetectionFinding, TelemetryEvent, AuditLog, User
from ..auth.security import current_user, require_roles
from .engine import matches, ALLOWED_FIELDS, ALLOWED_OPERATORS

router=APIRouter(prefix='/detections',tags=['detections'])

class RuleIn(BaseModel):
    name:str=Field(min_length=3,max_length=160)
    description:str=Field(default='',max_length=1000)
    rule_kind:str='sigma'
    severity:str='medium'
    event_type:str|None=None
    field_name:str
    operator:str='contains'
    expected_value:str=Field(min_length=1,max_length=512)
    mitre_attack:str|None=None
    enabled:bool=True
    @field_validator('rule_kind')
    @classmethod
    def kind(cls,v):
        if v not in ('sigma','suricata','yara'):raise ValueError('unsupported rule kind')
        return v
    @field_validator('severity')
    @classmethod
    def severity_choice(cls,v):
        if v not in ('low','medium','high','critical'):raise ValueError('invalid severity')
        return v
    @field_validator('field_name')
    @classmethod
    def valid_field(cls,v):
        if v not in ALLOWED_FIELDS:raise ValueError('unsupported field path')
        return v
    @field_validator('operator')
    @classmethod
    def valid_operator(cls,v):
        if v not in ALLOWED_OPERATORS:raise ValueError('unsupported operator')
        return v

def rule_data(r):
    return {x:getattr(r,x) for x in ('id','name','description','rule_kind','severity','event_type','field_name','operator','expected_value','mitre_attack','enabled','created_at')}

def finding_data(f):
    return {x:getattr(f,x) for x in ('id','rule_id','event_id','asset_id','severity','status','created_at')}

@router.get('/rules')
def list_rules(db:Session=Depends(get_db),actor:User=Depends(current_user)):
    return [rule_data(r) for r in db.scalars(select(DetectionRule).order_by(DetectionRule.created_at.desc()).limit(300))]

@router.post('/rules',status_code=201)
def create_rule(body:RuleIn,db:Session=Depends(get_db),actor:User=Depends(require_roles('Administrator','Detection Engineer','Purple Team Engineer'))):
    if db.scalar(select(DetectionRule.id).where(DetectionRule.name==body.name)):
        raise HTTPException(409,'Rule name already exists')
    obj=DetectionRule(**body.model_dump())
    db.add(obj);db.flush();db.add(AuditLog(actor_id=actor.id,action='created',resource='detection_rule',resource_id=obj.id));db.commit();db.refresh(obj)
    return rule_data(obj)

@router.patch('/rules/{rule_id}')
def toggle(rule_id:str, enabled:bool,db:Session=Depends(get_db),actor:User=Depends(require_roles('Administrator','Detection Engineer','Purple Team Engineer'))):
    rule=db.get(DetectionRule,rule_id)
    if not rule:raise HTTPException(404,'Rule not found')
    rule.enabled=enabled;db.add(AuditLog(actor_id=actor.id,action='enabled' if enabled else 'disabled',resource='detection_rule',resource_id=rule.id));db.commit();return rule_data(rule)

@router.post('/evaluate')
def evaluate(limit:int=Query(500,ge=1,le=2000),db:Session=Depends(get_db),actor:User=Depends(require_roles('Administrator','Detection Engineer','Purple Team Engineer'))):
    rules=list(db.scalars(select(DetectionRule).where(DetectionRule.enabled.is_(True))).all())
    events=list(db.scalars(select(TelemetryEvent).order_by(TelemetryEvent.received_at.desc()).limit(limit)).all())
    existing=set(db.execute(select(DetectionFinding.rule_id,DetectionFinding.event_id).where(DetectionFinding.event_id.in_([e.id for e in events]))).all()) if events else set()
    created=0
    for e in events:
        for r in rules:
            if (r.id,e.id) in existing or not matches(r,e):continue
            db.add(DetectionFinding(rule_id=r.id,event_id=e.id,asset_id=e.asset_id,severity=r.severity));created+=1
    db.add(AuditLog(actor_id=actor.id,action='evaluated',resource='detection_rules'))
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Concurrent evaluation: retry to avoid duplicate findings')
    return {'evaluated_events':len(events),'enabled_rules':len(rules),'new_findings':created}

@router.get('/findings')
def findings(limit:int=Query(100,ge=1,le=200),db:Session=Depends(get_db),actor:User=Depends(current_user)):
    rows=db.execute(select(DetectionFinding,DetectionRule.name,TelemetryEvent.message).join(DetectionRule,DetectionFinding.rule_id==DetectionRule.id).join(TelemetryEvent,DetectionFinding.event_id==TelemetryEvent.id).order_by(DetectionFinding.created_at.desc()).limit(limit)).all()
    return [dict(finding_data(f),rule_name=n,event_message=m) for f,n,m in rows]

@router.get('/summary')
def summary(db:Session=Depends(get_db),actor:User=Depends(current_user)):
    return {'rules':db.scalar(select(func.count(DetectionRule.id))) or 0,'enabled':db.scalar(select(func.count(DetectionRule.id)).where(DetectionRule.enabled.is_(True))) or 0,'findings':db.scalar(select(func.count(DetectionFinding.id))) or 0}
