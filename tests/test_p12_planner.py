import pytest
from backend.response.planner import make_plan

def test_no_actions():
    x=make_plan('triage_checklist','proposal-1',None,'correlation-1')
    assert x['external_actions']==0 and x['vm_changes']==0 and x['mode']=='SIMULATION_ONLY'

def test_distinct_fingerprint():
    a=make_plan('triage_checklist','one','inc',None)
    b=make_plan('triage_checklist','two','inc',None)
    assert a['plan_fingerprint']!=b['plan_fingerprint']

def test_unknown_playbook_rejected():
    with pytest.raises(ValueError):make_plan('shell_exec','p','i',None)

def test_two_targets_rejected():
    with pytest.raises(ValueError):make_plan('triage_checklist','p','i','c')
