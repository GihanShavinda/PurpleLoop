"""Deterministic simulation steps only; never execute shell commands or touch infrastructure."""
from hashlib import sha256

ALLOWED = {'triage_checklist', 'containment_plan', 'evidence_preservation'}

def make_plan(playbook_key: str, proposal_id: str, incident_id: str | None, correlation_id: str | None) -> dict:
    if playbook_key not in ALLOWED:
        raise ValueError('Unsupported rehearsal playbook')
    target = incident_id or correlation_id
    if not target or (incident_id and correlation_id):
        raise ValueError('Exactly one existing target is required')
    steps = [
        'Verify registered target identity and analyst authorization',
        'Review linked telemetry and prior human decision',
        'Record hypothetical response effects; no command execution',
        'Document a reversible recovery plan for later manual review',
    ]
    fingerprint = sha256(f'{proposal_id}|{playbook_key}|{target}'.encode()).hexdigest()[:20]
    return {'mode':'SIMULATION_ONLY', 'external_actions':0, 'vm_changes':0, 'playbook':playbook_key,
            'target_type':'incident' if incident_id else 'correlation', 'target_id':target,
            'plan_fingerprint': fingerprint,'steps':steps,
            'disclaimer':'A recorded rollback only closes this hypothetical exercise; it does not revert infrastructure.'}
