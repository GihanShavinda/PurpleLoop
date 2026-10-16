from backend.release.evaluation import coverage_rate, evaluate

def test_no_denominator_is_unknown():
    assert coverage_rate(0,0) is None

def test_rate_uses_only_assessed_cases():
    assert coverage_rate(3,1) == 75.0

def test_missing_evidence_not_certified():
    s=evaluate({}, [])
    assert s['status']=='evidence_snapshot_not_certification'
    assert s['metrics']['observed_detection_rate_percent'] is None
    assert all(x['state']!='observed' for x in s['readiness'])

def test_evidence_is_explicitly_limited():
    s=evaluate({'assets':5,'sources_enabled':3,'sources_recent':2,'coverage':{'detected':1,'not_detected':1}},[{'passed':True},{'passed':False}])
    assert s['metrics']['observed_detection_rate_percent']==50.0
    assert s['metrics']['configuration_checks_passed']==1
    assert s['metrics']['configuration_checks_total']==2
    assert s['status']!='passed'
