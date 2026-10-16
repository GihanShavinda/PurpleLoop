from datetime import datetime,timezone,timedelta
import pytest
from backend.vmware_range.assessment import assess
NOW=datetime(2026,10,17,12,tzinfo=timezone.utc)
def test_ready_when_all_conditions_match():
    x=assess('poweredOn','VMnet1','vmnet1',NOW-timedelta(minutes=2),NOW)
    assert x['ready_for_manual_validation'] is True
def test_reported_power_not_proof():
    x=assess('poweredOff','VMnet1','VMnet1',NOW,NOW)
    assert not x['ready_for_manual_validation']
def test_stale_telemetry():
    x=assess('poweredOn','VMnet1','VMnet1',NOW-timedelta(hours=1),NOW)
    assert not x['checks']['recent_telemetry_receipt']
def test_wrong_network():
    x=assess('poweredOn','VMnet1','NAT',NOW,NOW)
    assert not x['checks']['network_label_matches']
def test_bad_power_state_rejected():
    with pytest.raises(ValueError): assess('sudo shutdown','VMnet1','VMnet1',NOW,NOW)
