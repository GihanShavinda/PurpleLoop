import pytest
from backend.soar.playbooks import PLAYBOOKS, simulate

def test_all_playbooks_are_dry_run():
    for key in PLAYBOOKS:
        r=simulate(key,'approved isolated laboratory test')
        assert r['mode']=='dry_run' and r['performed_actions']==[]
        assert len(r['steps'])>0

def test_unknown_playbook_rejected():
    with pytest.raises(ValueError):simulate('execute_powershell','reason')

def test_simulations_do_not_mutate_inputs():
    justification='Validate an existing P9 case'
    assert simulate('triage_checklist',justification)['source_justification']==justification
