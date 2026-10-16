from backend.investigation.composer import compose

def test_no_claim_of_compromise():
    r=compose('ubuntu2404',[{'id':'evt1','run_id':'run1','bucket_start':'2026-10-16T00:00:00Z','event_count':213,'anomaly_score':0.1}])
    assert r['assessment']=='undetermined'
    assert 'not proof' in r['limitations'][0].lower()

def test_bounded_evidence():
    rows=[{'id':str(i),'run_id':'run','bucket_start':'time','event_count':1,'anomaly_score':.1} for i in range(40)]
    assert len(compose('host',rows)['evidence'])==25

def test_correlation_not_invented():
    assert not any(x['kind']=='correlation_case' for x in compose('host',[])['evidence'])

def test_correlation_references_real_input():
    c={'id':'case1','risk_score':34,'finding_count':2,'indicator_count':1}
    assert compose('host',[],c)['evidence'][0]['id']=='case1'
