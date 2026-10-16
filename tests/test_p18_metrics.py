from datetime import datetime, timezone, timedelta
from backend.operations.metrics import detection_rate, freshness

def test_empty_coverage_is_unknown(): assert detection_rate(0,0) is None
def test_coverage_uses_only_assessed_scenarios(): assert detection_rate(3,1)==75.0
def test_recent_receipt():
    now=datetime.now(timezone.utc)
    assert freshness(now-timedelta(minutes=4),now)
    assert not freshness(now-timedelta(minutes=12),now)
def test_missing_receipt(): assert not freshness(None,datetime.now(timezone.utc))
