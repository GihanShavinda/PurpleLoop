"""Authenticated bounded read-only cross-milestone metrics."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user
from ..models import (User, Asset, TelemetrySource, TelemetryEvent, DetectionFinding,
    IncidentCase, DetectionCoverageAssessment, AnomalyAnalysisRun,
    InvestigationDraft, VmwareReadinessCheck, CorrelationCase)
from .metrics import detection_rate, freshness

router = APIRouter(prefix="/operations", tags=["P18 Operations Dashboard"])

@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    recent = now - timedelta(minutes=10)
    # Constant number of indexed / grouped queries. Never load raw event payloads.
    asset_count = db.scalar(select(func.count(Asset.id))) or 0
    total_sources = db.scalar(select(func.count(TelemetrySource.id)).where(TelemetrySource.enabled.is_(True))) or 0
    recent_sources = db.scalar(select(func.count(TelemetrySource.id)).where(TelemetrySource.enabled.is_(True), TelemetrySource.last_seen_at >= recent)) or 0
    events24 = db.scalar(select(func.count(TelemetryEvent.id)).where(TelemetryEvent.received_at >= since)) or 0
    findings24 = db.scalar(select(func.count(DetectionFinding.id)).where(DetectionFinding.created_at >= since)) or 0
    incidents_open = db.scalar(select(func.count(IncidentCase.id)).where(IncidentCase.status.in_(['open','investigating']))) or 0
    correlations24 = db.scalar(select(func.count(CorrelationCase.id)).where(CorrelationCase.created_at >= since)) or 0
    outcomes = dict(db.execute(select(DetectionCoverageAssessment.outcome,func.count(DetectionCoverageAssessment.id)).group_by(DetectionCoverageAssessment.outcome)).all())
    detected = outcomes.get('detected',0)
    missed = outcomes.get('not_detected',0)
    anomaly_runs = db.scalar(select(func.count(AnomalyAnalysisRun.id)).where(AnomalyAnalysisRun.created_at >= since)) or 0
    anomalies24 = db.scalar(select(func.coalesce(func.sum(AnomalyAnalysisRun.anomaly_count),0)).where(AnomalyAnalysisRun.created_at >= since)) or 0
    reports = dict(db.execute(select(InvestigationDraft.status,func.count(InvestigationDraft.id)).group_by(InvestigationDraft.status)).all())
    latest_checks = db.scalars(select(VmwareReadinessCheck).order_by(VmwareReadinessCheck.checked_at.desc()).limit(100)).all()
    latest_by_asset = {}
    for record in latest_checks:
        latest_by_asset.setdefault(record.asset_id,record)
    assets = db.scalars(select(Asset).order_by(Asset.hostname).limit(100)).all()
    # Last telemetry receipts come from real stored events rather than manual power-state labels.
    receipts = dict(db.execute(select(TelemetryEvent.asset_id,func.max(TelemetryEvent.received_at)).group_by(TelemetryEvent.asset_id)).all())
    rows = []
    for asset in assets:
        check = latest_by_asset.get(asset.id)
        receipt = receipts.get(asset.id)
        rows.append({'id':asset.id,'hostname':asset.hostname,'criticality':asset.criticality,
          'vmware_network':asset.vmware_network,'last_receipt':receipt,
          'receiving':freshness(receipt,now),
          'manual_ready':(check.assessment_json or {}).get('ready_for_manual_validation') if check else None,
          'readiness_checked_at':check.checked_at if check else None})
    return {'generated_at':now,'window_hours':24,'assets':asset_count,'sources_enabled':total_sources,
      'sources_recent':recent_sources,'events_24h':events24,'findings_24h':findings24,
      'open_incidents':incidents_open,'correlations_24h':correlations24,
      'coverage':{'detected':detected,'not_detected':missed,'inconclusive':outcomes.get('inconclusive',0),
                  'rate_percent':detection_rate(detected,missed)},
      'anomaly_runs_24h':anomaly_runs,'outliers_24h':int(anomalies24),
      'investigations':reports,'lab_assets':rows,
      'limitations':['Source freshness uses collector timestamps; it is not proof of full host coverage.',
        'Readiness is based partly on operator-reported information.',
        'Coverage rate uses only explicitly assessed P14 scenarios, not the ATT&CK matrix.',
        'Anomaly outliers do not establish malicious activity.']}
