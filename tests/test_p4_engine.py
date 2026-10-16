from types import SimpleNamespace
from backend.detections.engine import matches,field_value

def rule(**kw):
    return SimpleNamespace(enabled=True,event_type=None,field_name='message',operator='contains',expected_value='powershell',**kw)

def test_contains_case_insensitive():
    event=SimpleNamespace(event_type='sysmon.1',message='Started PowerShell.exe',payload={})
    assert matches(rule(),event)

def test_event_type_filter():
    event=SimpleNamespace(event_type='suricata.flow',message='PowerShell',payload={})
    r=SimpleNamespace(enabled=True,event_type='sysmon.1',field_name='message',operator='contains',expected_value='powershell')
    assert not matches(r,event)

def test_nested_alert():
    event=SimpleNamespace(event_type='suricata.alert',message='alert',payload={'alert':{'signature':'ET TEST Lab'}})
    r=SimpleNamespace(enabled=True,event_type=None,field_name='payload.alert.signature',operator='contains',expected_value='test')
    assert matches(r,event)

def test_unknown_field_fails_closed():
    assert field_value(SimpleNamespace(payload={'secret':'yes'}),'payload.secret') is None
