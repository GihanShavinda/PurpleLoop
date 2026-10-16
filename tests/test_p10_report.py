from backend.analyst.report import build_report, MAX_EVIDENCE

def sample():
    return {'asset_label':'ubuntu2404','risk_score':34}

def test_evidence_only():
    r=build_report(sample(),[{'event_id':'x','timestamp':'2026-10-16T10:00:00Z','kind':'finding','event_type':'linux_journal','message':'Test'}])
    assert r['evidence_count']==1
    assert r['attack_techniques']==[]
    assert r['requires_human_review'] is True

def test_empty_evidence_is_not_fabricated():
    r=build_report(sample(),[])
    assert r['evidence_count']==0 and r['timeline']==[]

def test_bounded_and_truncated():
    data=[{'event_id':str(i),'timestamp':'x','kind':'finding','message':'Z'*1000} for i in range(70)]
    r=build_report(sample(),data)
    assert len(r['timeline'])==MAX_EVIDENCE
    assert all(len(x['description'])<=240 for x in r['timeline'])

def test_distinct_evidence_kinds():
    data=[{'event_id':'a','timestamp':'x','kind':'finding'},{'event_id':'b','timestamp':'x','kind':'intelligence'}]
    assert build_report(sample(),data)['kind_counts']=={'finding':1,'intelligence':1}
