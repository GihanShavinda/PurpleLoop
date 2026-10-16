from backend.incidents.service import validate_transition, related_finding_ids

def test_statuses():
    assert validate_transition('open', 'investigating')
    assert validate_transition('investigating', 'resolved')
    assert not validate_transition('open', 'resolved')
    assert validate_transition('resolved', 'investigating')

def test_deterministic_bounded_correlation():
    rows=[('a','asset1'),('b','asset2'),('c','asset1'),('a','asset1')]
    assert related_finding_ids(rows,'asset1',[],limit=10)==['a','c']
    assert related_finding_ids(rows,'asset1',['a'],limit=1)==['c']

def test_invalid_states():
    assert not validate_transition('bogus','open')
    assert not validate_transition('open','bogus')
