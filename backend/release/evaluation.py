"""Pure evidence summaries: unknown is never converted to pass."""
from datetime import datetime, timezone

def coverage_rate(detected, not_detected):
    total = detected + not_detected
    return round(100 * detected / total, 2) if total else None

def evaluate(overview, assurance_checks):
    coverage = overview.get('coverage') or {}
    found = int(coverage.get('detected') or 0)
    missed = int(coverage.get('not_detected') or 0)
    sources = int(overview.get('sources_enabled') or 0)
    fresh = int(overview.get('sources_recent') or 0)
    assets = int(overview.get('assets') or 0)
    checks = list(assurance_checks)
    passed = sum(1 for c in checks if c.get('passed') is True)
    return {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'status': 'evidence_snapshot_not_certification',
        'metrics': {
            'registered_assets': assets,
            'enabled_collectors': sources,
            'collectors_recent_10m': fresh,
            'events_last_24h': int(overview.get('events_24h') or 0),
            'findings_last_24h': int(overview.get('findings_24h') or 0),
            'open_incidents': int(overview.get('open_incidents') or 0),
            'correlations_last_24h': int(overview.get('correlations_24h') or 0),
            'detected_assessments': found,
            'not_detected_assessments': missed,
            'observed_detection_rate_percent': coverage_rate(found, missed),
            'anomaly_runs_last_24h': int(overview.get('anomaly_runs_24h') or 0),
            'outliers_last_24h': int(overview.get('outliers_24h') or 0),
            'configuration_checks_passed': passed,
            'configuration_checks_total': len(checks),
        },
        'readiness': [
            {'id':'inventory_present','state':'observed' if assets else 'not_observed', 'detail':'Registered inventory exists' if assets else 'No registered assets'},
            {'id':'telemetry_recent','state':'observed' if fresh else 'not_observed','detail':f'{fresh} of {sources} enabled sources recently seen'},
            {'id':'detection_validation','state':'observed' if found + missed else 'not_observed','detail':f'{found + missed} explicitly assessed P14 cases'},
            {'id':'configuration_checks','state':'observed' if checks and passed == len(checks) else 'needs_review','detail':f'{passed}/{len(checks)} evaluated checks passed'},
        ],
        'limitations': [
            'Counts are sampled from the current database and are not a benchmark or SLA.',
            'P14 measured rate covers selected lab scenarios only, not MITRE ATT&CK-wide coverage.',
            'Fresh telemetry does not prove all events were collected.',
            'P15 statistical outliers do not prove attacks.',
            'P17 power and network labels include operator-reported values.',
            'P19 configuration checks are not an external penetration test.',
            'Performance, reliability, RBAC and cross-host replay must be demonstrated separately.',
            'No vulnerabilities, exploits, guest commands, VMware changes, or SOAR actions executed by this endpoint.',
        ],
    }
