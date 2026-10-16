from backend.simulation.scenarios import SCENARIOS,render_command
import pytest
def test_only_benign_scenario_is_allowlisted():
    assert list(SCENARIOS)==['ubuntu_journal_marker']
def test_marker_command_escaped_by_strict_validation():
    assert render_command('ubuntu_journal_marker','PF13-a123')=='logger -t purpleforge-p13 "PF13-a123"'
def test_invalid_marker_rejected():
    with pytest.raises(ValueError):render_command('ubuntu_journal_marker','PF13-test;reboot')
def test_unapproved_scenario_rejected():
    with pytest.raises(ValueError):render_command('remote_exec','PF13-a123')
