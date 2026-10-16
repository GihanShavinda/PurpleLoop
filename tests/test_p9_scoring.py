from backend.correlation.scoring import score

def test_empty():
    value,reasons=score([],[],'low')
    assert value==0 and reasons['note']

def test_bounded():
    value,_=score(['critical']*100,[100]*100,'critical')
    assert value<=100

def test_case_normalization():
    assert score(['HIGH'],[50],'medium')[0]==score(['high'],[50],'medium')[0]

def test_rationale():
    n,reasons=score(['high'],[80],'critical')
    assert n==43 and reasons['asset_points']==15
