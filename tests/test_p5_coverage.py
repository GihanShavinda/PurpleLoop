from types import SimpleNamespace as N
from backend.validation.coverage import valid_technique,outcome,coverage_stats

def test_ids():
    assert valid_technique('T1059') and valid_technique('T1059.001')
    assert not valid_technique('invalid') and not valid_technique('T1059; DROP TABLE')

def test_outcomes():
    assert outcome(['f1'])=='passed'
    assert outcome([])=='failed'
    assert outcome(['f1'],False)=='inconclusive'

def test_coverage():
    ss=[N(id='a',enabled=True),N(id='b',enabled=True),N(id='c',enabled=False)]
    rr=[N(scenario_id='a',status='passed'),N(scenario_id='b',status='failed')]
    assert coverage_stats(ss,rr)=={'enabled_scenarios':2,'tested_scenarios':2,'passed_scenarios':1,'coverage_percent':50.0}
