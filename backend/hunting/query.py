"""Bounded filters for the P7 hunting API. No arbitrary SQL, regex, or shell execution."""
from datetime import datetime, timedelta, timezone
import ipaddress

MAX_RANGE_DAYS = 7
ALLOWED_KINDS = ('ip', 'domain', 'hash', 'process')

def validate_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError('Both timestamps must have timezone offsets')
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if start >= end or end - start > timedelta(days=MAX_RANGE_DAYS):
        raise ValueError('Time window must be positive and no longer than 7 days')
    if end > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('End time is too far in the future')
    return start, end

def escaped_contains(value: str) -> str:
    return '%' + value.replace(chr(92), chr(92)*2).replace('%', chr(92)+'%').replace('_', chr(92)+'_') + '%'

def normalize_ioc(kind: str, value: str) -> str:
    value=value.strip()
    if kind not in ALLOWED_KINDS or not 2 <= len(value) <= 255:
        raise ValueError('Invalid IOC kind or length')
    if kind == 'ip':
        return str(ipaddress.ip_address(value))
    if any(c in value for c in ('\n', '\r', '\x00')):
        raise ValueError('Invalid IOC characters')
    if kind == 'hash' and (len(value) not in (32,40,64) or any(c not in '0123456789abcdefABCDEF' for c in value)):
        raise ValueError('Invalid hash')
    if kind == 'domain' and (len(value)>253 or not all(part and len(part)<=63 and all(c.isalnum() or c=='-' for c in part) and not part.startswith('-') and not part.endswith('-') for part in value.lower().split('.'))):
        raise ValueError('Invalid domain')
    return value.lower() if kind in ('domain','hash') else value
