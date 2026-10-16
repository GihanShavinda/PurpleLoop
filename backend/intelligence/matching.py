"""P8 reviewed IOC matching against normalized telemetry; no outbound connections."""
from ..hunting.query import normalize_ioc

INDICATOR_FIELDS = {
    'ip': ('src_ip','dest_ip','SourceIp','DestinationIp'),
    'domain': ('QueryName','query','hostname'),
    'hash': ('Hashes','hash','sha256'),
    'process': ('Image','CommandLine','image','process_name'),
}

def canonical(kind: str, value: str) -> str:
    if kind not in INDICATOR_FIELDS:
        raise ValueError('Unsupported indicator type')
    return normalize_ioc(kind, value)

def event_contains(kind: str, value: str, message: str, payload: dict) -> bool:
    """Conservative check over allowlisted keys; never search arbitrary JSON blobs."""
    value=canonical(kind, value)
    values=[message or '']
    for field in INDICATOR_FIELDS[kind]:
        v=(payload or {}).get(field)
        if isinstance(v,(str,int,float)):
            values.append(str(v))
    hay=[v.lower() for v in values]
    target=value.lower()
    if kind == 'ip':
        # Avoid partial IP matches, e.g. 192.168.1.1 against 192.168.1.10
        import re
        pat=re.compile(r'(?<![0-9a-fA-F:.])'+re.escape(target)+r'(?![0-9a-fA-F:.])',re.I)
        return any(pat.search(v) for v in values)
    if kind=='domain':
        import re
        pat=re.compile(r'(?<![a-z0-9.-])'+re.escape(target)+r'(?![a-z0-9.-])', re.I)
        return any(pat.search(v) for v in values)
    return any(target in x for x in hay)
