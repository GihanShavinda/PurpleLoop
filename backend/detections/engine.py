"""Deterministic single-field matches. No eval, arbitrary code, or remote execution."""
from collections.abc import Mapping

ALLOWED_OPERATORS = {'equals','contains','startswith','endswith'}
ALLOWED_FIELDS = {'event_type','message','severity','payload.EventID','payload.EventId','payload.event_type','payload.Image','payload.CommandLine','payload.DestinationIp','payload.DestinationPort','payload.QueryName','payload.alert.signature','payload.alert.signature_id','payload.proto','payload.src_ip','payload.dest_ip'}

def field_value(event, field):
    if field not in ALLOWED_FIELDS: return None
    if not field.startswith('payload.'):
        return getattr(event,field,None)
    value=getattr(event,'payload',{})
    for part in field.split('.')[1:]:
        if not isinstance(value,Mapping): return None
        value=value.get(part)
    return value

def matches(rule,event):
    if not rule.enabled or (rule.event_type and rule.event_type!=event.event_type):return False
    found=field_value(event,rule.field_name)
    if found is None:return False
    a=str(found).casefold();b=rule.expected_value.casefold()
    return {'equals':lambda:a==b,'contains':lambda:b in a,'startswith':lambda:a.startswith(b),'endswith':lambda:a.endswith(b)}[rule.operator]()
