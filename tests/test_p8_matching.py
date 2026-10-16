import pytest
from backend.intelligence.matching import canonical, event_contains

def test_ip_canonical():
    assert canonical('ip','192.168.37.20')=='192.168.37.20'

def test_invalid_ip():
    with pytest.raises(ValueError):canonical('ip','bad_ip')

def test_ip_no_partial_false_positive():
    assert not event_contains('ip','192.168.37.2','192.168.37.20',{})

def test_ip_payload_match():
    assert event_contains('ip','192.168.37.20','flow',{'src_ip':'192.168.37.20'})

def test_domain_boundary():
    assert not event_contains('domain','example.org','notexample.org',{})

def test_process_field():
    assert event_contains('process','powershell.exe','created',{'Image':r'C:\Windows\powershell.exe'})
