"""Deterministic readiness from reported metadata and verified receipts."""
from datetime import datetime, timezone, timedelta
ALLOWED_STATES = ('poweredOn','poweredOff','suspended','unknown')
def assess(power_state: str, expected_network: str | None, reported_network: str, last_event: datetime | None, checked_at: datetime) -> dict:
    if power_state not in ALLOWED_STATES: raise ValueError('Invalid power state')
    if checked_at.tzinfo is None: raise ValueError('Timestamp must be timezone-aware')
    if last_event is not None and last_event.tzinfo is None: raise ValueError('Timestamp must be timezone-aware')
    telemetry_recent = bool(last_event and checked_at - timedelta(minutes=10) <= last_event <= checked_at + timedelta(minutes=1))
    network_matches = bool(expected_network and reported_network and expected_network.strip().casefold() == reported_network.strip().casefold())
    checks={'reported_powered_on':power_state=='poweredOn','network_label_matches':network_matches,'recent_telemetry_receipt':telemetry_recent}
    # Do not claim verified VM power or layer-2 network visibility.
    return {'checks':checks,'ready_for_manual_validation':all(checks.values()),'limitations':['Power state and network are operator reported, not independently verified','Telemetry receipt only proves recent events were ingested','No VMware commands, probing, snapshots, or changes were performed']}
