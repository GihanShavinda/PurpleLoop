from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, Integer, UniqueConstraint, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def now():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid4())

class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    users: Mapped[list[User]] = relationship(back_populates='role')

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey('roles.id'), nullable=False)
    role: Mapped[Role] = relationship(back_populates='users')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Lab(Base):
    __tablename__ = 'labs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    assets: Mapped[list[Asset]] = relationship(back_populates='lab')

class Asset(Base):
    __tablename__ = 'assets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lab_id: Mapped[str] = mapped_column(ForeignKey('labs.id'), nullable=False)
    lab: Mapped[Lab] = relationship(back_populates='assets')
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    mac_address: Mapped[str | None] = mapped_column(String(17))
    operating_system: Mapped[str | None] = mapped_column(String(120))
    asset_type: Mapped[str] = mapped_column(String(80), default='vm')
    environment: Mapped[str] = mapped_column(String(80), default='lab')
    criticality: Mapped[str] = mapped_column(String(20), default='medium')
    owner: Mapped[str | None] = mapped_column(String(150))
    vm_name: Mapped[str | None] = mapped_column(String(150))
    vmware_network: Mapped[str | None] = mapped_column(String(100))
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (UniqueConstraint('lab_id','hostname',name='uq_asset_lab_hostname'),)

class NetworkInterface(Base):
    __tablename__ = 'network_interfaces'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    mac_address: Mapped[str | None] = mapped_column(String(17))

class TelemetrySource(Base):
    __tablename__ = 'telemetry_sources'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str | None] = mapped_column(String(150))
    token_sha256: Mapped[str | None] = mapped_column(String(64), unique=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TelemetryEvent(Base):
    __tablename__ = 'telemetry_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(ForeignKey('telemetry_sources.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default='info')
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    __table_args__ = (Index('ix_pf_events_asset_time','asset_id','event_time'),)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class RefreshSession(Base):
    __tablename__ = 'refresh_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class DetectionRule(Base):
    __tablename__ = 'detection_rules'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    rule_kind: Mapped[str] = mapped_column(String(24), nullable=False, default='sigma')
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default='medium')
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_type: Mapped[str | None] = mapped_column(String(120))
    field_name: Mapped[str] = mapped_column(String(160), nullable=False)
    operator: Mapped[str] = mapped_column(String(24), nullable=False)
    expected_value: Mapped[str] = mapped_column(String(512), nullable=False)
    mitre_attack: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class DetectionFinding(Base):
    __tablename__ = 'detection_findings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_id: Mapped[str] = mapped_column(ForeignKey('detection_rules.id'), nullable=False)
    event_id: Mapped[str] = mapped_column(ForeignKey('telemetry_events.id'), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint('rule_id','event_id',name='uq_pf_detection_rule_event'),)


class ValidationScenario(Base):
    __tablename__ = 'validation_scenarios'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    rule_id: Mapped[str] = mapped_column(ForeignKey('detection_rules.id'), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'), nullable=False)
    technique_id: Mapped[str] = mapped_column(String(24), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ValidationRun(Base):
    __tablename__ = 'validation_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey('validation_scenarios.id'), nullable=False)
    started_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='running')
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class ValidationEvidence(Base):
    __tablename__ = 'validation_evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey('validation_runs.id'), nullable=False)
    finding_id: Mapped[str] = mapped_column(ForeignKey('detection_findings.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint('run_id','finding_id',name='uq_pf_validation_evidence'),)


class IncidentCase(Base):
    __tablename__ = 'incident_cases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='open')
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)

class IncidentFinding(Base):
    __tablename__ = 'incident_findings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('incident_cases.id', ondelete='CASCADE'), nullable=False, index=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey('detection_findings.id'), nullable=False, unique=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class IncidentNote(Base):
    __tablename__ = 'incident_notes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('incident_cases.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class SavedHunt(Base):
    __tablename__ = 'saved_hunts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class HuntEvidence(Base):
    __tablename__ = 'hunt_evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('incident_cases.id', ondelete='CASCADE'), nullable=False)
    event_id: Mapped[str] = mapped_column(ForeignKey('telemetry_events.id'), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('case_id','event_id',name='uq_p7_case_event'),)


class IntelligenceIndicator(Base):
    __tablename__ = 'intelligence_indicators'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    source_label: Mapped[str] = mapped_column(String(160), nullable=False, default='manual')
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('kind', 'value', name='uq_p8_indicator_kind_value'),)

class IntelligenceMatch(Base):
    __tablename__ = 'intelligence_matches'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    indicator_id: Mapped[str] = mapped_column(ForeignKey('intelligence_indicators.id'), nullable=False)
    event_id: Mapped[str] = mapped_column(ForeignKey('telemetry_events.id'), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('indicator_id', 'event_id', name='uq_p8_indicator_event'),)


class CorrelationCase(Base):
    __tablename__ = 'correlation_cases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'), nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_reasons: Mapped[dict] = mapped_column(JSON, nullable=False)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False)
    indicator_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='new')
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('asset_id','window_start','window_end',name='uq_p9_asset_window'),)

class CorrelationEvidence(Base):
    __tablename__ = 'correlation_evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    correlation_id: Mapped[str] = mapped_column(ForeignKey('correlation_cases.id',ondelete='CASCADE'), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('telemetry_events.id'), nullable=False)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey('detection_findings.id'))
    intelligence_match_id: Mapped[str | None] = mapped_column(ForeignKey('intelligence_matches.id'))
    evidence_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    __table_args__ = (UniqueConstraint('correlation_id','evidence_kind','event_id',name='uq_p9_case_kind_event'),)


class AnalystReport(Base):
    """Immutable generated snapshot with explicit human review state."""
    __tablename__ = 'analyst_reports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    correlation_id: Mapped[str] = mapped_column(ForeignKey('correlation_cases.id'), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(32), nullable=False, default='evidence-v1')
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='draft')
    review_note: Mapped[str] = mapped_column(Text, nullable=False, default='')
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SoarProposal(Base):
    __tablename__ = 'soar_proposals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    playbook_key: Mapped[str] = mapped_column(String(64), nullable=False)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey('incident_cases.id'))
    correlation_id: Mapped[str | None] = mapped_column(ForeignKey('correlation_cases.id'))
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='pending')
    proposed_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    decision_note: Mapped[str] = mapped_column(Text, nullable=False, default='')
    output_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class SoarAudit(Base):
    __tablename__ = 'soar_audit'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey('soar_proposals.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
