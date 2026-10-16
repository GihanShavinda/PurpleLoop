from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (IncidentCase, IncidentFinding, IncidentNote, DetectionFinding,
                      DetectionRule, TelemetryEvent, Asset, User, AuditLog)
from ..auth.security import current_user, require_roles
from .service import SEVERITIES, STATUSES, validate_transition, related_finding_ids

router = APIRouter(prefix='/incidents', tags=['P6 incidents'])
WRITERS = ('Administrator', 'Purple Team Engineer', 'SOC Analyst', 'Detection Engineer')

def out(case, count=0):
    return {key: getattr(case, key) for key in
            ('id', 'title', 'description', 'asset_id', 'severity', 'status',
             'assignee_id', 'created_by', 'created_at', 'updated_at')} | {'finding_count': count}

def assert_case(db, case_id):
    case = db.get(IncidentCase, case_id)
    if case is None:
        raise HTTPException(404, 'Incident not found')
    return case

class CreateCase(BaseModel):
    finding_id: str
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(default='', max_length=2000)
    assignee_id: str | None = None

@router.post('', status_code=201)
def create(body: CreateCase, db: Session=Depends(get_db), actor: User=Depends(require_roles(*WRITERS))):
    finding = db.get(DetectionFinding, body.finding_id)
    if not finding:
        raise HTTPException(422, 'Unknown detection finding')
    if db.scalar(select(IncidentFinding.id).where(IncidentFinding.finding_id == finding.id)):
        raise HTTPException(409, 'Finding is already linked to a case')
    if body.assignee_id and not db.get(User, body.assignee_id):
        raise HTTPException(422, 'Unknown assignee')
    case = IncidentCase(title=body.title, description=body.description,
        asset_id=finding.asset_id, severity=finding.severity,
        assignee_id=body.assignee_id, created_by=actor.id)
    db.add(case)
    db.flush()
    db.add(IncidentFinding(case_id=case.id, finding_id=finding.id))
    db.add(AuditLog(actor_id=actor.id, action='created', resource='incident_case', resource_id=case.id))
    db.commit()
    db.refresh(case)
    return out(case, 1)

@router.get('')
def list_cases(status: str | None=None, limit: int=Query(100, ge=1, le=200),
               db: Session=Depends(get_db), actor: User=Depends(current_user)):
    if status is not None and status not in STATUSES:
        raise HTTPException(422, 'Invalid status')
    statement = select(IncidentCase).order_by(IncidentCase.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(IncidentCase.status == status)
    cases = db.scalars(statement).all()
    counts = dict(db.execute(select(IncidentFinding.case_id, func.count())
       .where(IncidentFinding.case_id.in_([c.id for c in cases]))
       .group_by(IncidentFinding.case_id)).all()) if cases else {}
    return [out(c, counts.get(c.id, 0)) for c in cases]

@router.get('/summary')
def summary(db: Session=Depends(get_db), actor: User=Depends(current_user)):
    counts = dict(db.execute(select(IncidentCase.status, func.count()).group_by(IncidentCase.status)).all())
    return {'total': sum(counts.values()), 'by_status': {s: counts.get(s, 0) for s in STATUSES}}

@router.get('/unlinked-findings')
def unlinked_findings(limit: int=Query(40, ge=1, le=100), db: Session=Depends(get_db),
                      actor: User=Depends(current_user)):
    rows = db.execute(select(DetectionFinding, DetectionRule.name, TelemetryEvent.message)
        .join(DetectionRule, DetectionFinding.rule_id == DetectionRule.id)
        .join(TelemetryEvent, DetectionFinding.event_id == TelemetryEvent.id)
        .outerjoin(IncidentFinding, IncidentFinding.finding_id == DetectionFinding.id)
        .where(IncidentFinding.id.is_(None))
        .order_by(DetectionFinding.created_at.desc()).limit(limit)).all()
    return [{'id': f.id, 'asset_id': f.asset_id, 'severity': f.severity,
             'rule_name': name, 'message': msg[:300], 'created_at': f.created_at}
            for f, name, msg in rows]

@router.get('/{case_id}')
def details(case_id: str, db: Session=Depends(get_db), actor: User=Depends(current_user)):
    case = assert_case(db, case_id)
    findings = db.execute(select(IncidentFinding.finding_id, DetectionRule.name,
      TelemetryEvent.event_time, TelemetryEvent.message)
        .join(DetectionFinding, DetectionFinding.id == IncidentFinding.finding_id)
        .join(DetectionRule, DetectionRule.id == DetectionFinding.rule_id)
        .join(TelemetryEvent, TelemetryEvent.id == DetectionFinding.event_id)
        .where(IncidentFinding.case_id == case.id).order_by(TelemetryEvent.event_time.desc()).limit(100)).all()
    notes = db.scalars(select(IncidentNote).where(IncidentNote.case_id == case.id)
       .order_by(IncidentNote.created_at.desc()).limit(100)).all()
    return {'case': out(case, len(findings)),
            'findings': [{'id': fid, 'rule_name': rule, 'event_time': ts, 'message': msg[:1000]}
                        for fid, rule, ts, msg in findings],
            'notes': [{'id': n.id, 'note': n.note, 'actor_id': n.actor_id,
                       'created_at': n.created_at} for n in notes]}

class UpdateCase(BaseModel):
    status: str | None = None
    assignee_id: str | None = None

@router.patch('/{case_id}')
def update(case_id: str, body: UpdateCase, db: Session=Depends(get_db),
           actor: User=Depends(require_roles(*WRITERS))):
    case = assert_case(db, case_id)
    if body.status is None and 'assignee_id' not in body.model_fields_set:
        raise HTTPException(422, 'Provide status or assignee_id')
    if body.status is not None:
        if not validate_transition(case.status, body.status):
            raise HTTPException(422, f'Invalid transition: {case.status} -> {body.status}')
        case.status = body.status
    if 'assignee_id' in body.model_fields_set:
        if body.assignee_id and not db.get(User, body.assignee_id):
            raise HTTPException(422, 'Unknown assignee')
        case.assignee_id = body.assignee_id
    db.add(AuditLog(actor_id=actor.id, action='updated', resource='incident_case', resource_id=case.id))
    db.commit()
    db.refresh(case)
    return out(case)

class NoteIn(BaseModel):
    note: str = Field(min_length=3, max_length=2000)

@router.post('/{case_id}/notes', status_code=201)
def add_note(case_id: str, body: NoteIn, db: Session=Depends(get_db),
             actor: User=Depends(require_roles(*WRITERS))):
    assert_case(db, case_id)
    note = IncidentNote(case_id=case_id, actor_id=actor.id, note=body.note)
    db.add(note)
    db.add(AuditLog(actor_id=actor.id, action='noted', resource='incident_case', resource_id=case_id))
    db.commit()
    db.refresh(note)
    return {'id': note.id, 'note': note.note, 'created_at': note.created_at}

class LinkIn(BaseModel):
    finding_id: str

@router.post('/{case_id}/findings', status_code=201)
def attach(case_id: str, body: LinkIn, db: Session=Depends(get_db),
           actor: User=Depends(require_roles(*WRITERS))):
    case = assert_case(db, case_id)
    finding = db.get(DetectionFinding, body.finding_id)
    if not finding or finding.asset_id != case.asset_id:
        raise HTTPException(422, 'Finding must exist and belong to the same asset')
    if db.scalar(select(IncidentFinding.id).where(IncidentFinding.finding_id == finding.id)):
        raise HTTPException(409, 'Finding already linked')
    db.add(IncidentFinding(case_id=case.id, finding_id=finding.id))
    db.add(AuditLog(actor_id=actor.id, action='attached_finding', resource='incident_case', resource_id=case.id))
    db.commit()
    return {'linked': True}

@router.post('/{case_id}/correlate')
def correlate(case_id: str, minutes: int=Query(60, ge=1, le=1440),
              db: Session=Depends(get_db), actor: User=Depends(require_roles(*WRITERS))):
    case = assert_case(db, case_id)
    if case.status in ('resolved', 'false_positive'):
        raise HTTPException(409, 'Reopen case before correlating')
    start = case.created_at - timedelta(minutes=minutes)
    rows = db.execute(select(DetectionFinding.id, DetectionFinding.asset_id)
        .outerjoin(IncidentFinding, IncidentFinding.finding_id == DetectionFinding.id)
        .where(DetectionFinding.asset_id == case.asset_id,
               DetectionFinding.created_at >= start,
               DetectionFinding.created_at <= datetime.now(timezone.utc),
               IncidentFinding.id.is_(None))
        .order_by(DetectionFinding.created_at.desc()).limit(100)).all()
    ids = related_finding_ids(rows, case.asset_id, [], limit=25)
    for fid in ids:
        db.add(IncidentFinding(case_id=case.id, finding_id=fid))
    db.add(AuditLog(actor_id=actor.id, action='correlated', resource='incident_case', resource_id=case.id))
    db.commit()
    return {'linked_count': len(ids), 'method': 'same_asset_and_time_window', 'automatic_actions': False}
