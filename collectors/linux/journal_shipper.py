#!/usr/bin/env python3
"""PurpleForge P3.1: journald -> authenticated P3 ingest, without containers.

Requires Linux with journalctl and Python 3.10+. Run as a dedicated member of
systemd-journal, never as root unless journal access strictly requires it.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def to_event(record):
    """Map one journal record to the P3 schema; avoid transmitting raw journal data."""
    timestamp = record.get('__REALTIME_TIMESTAMP')
    try:
        event_time = datetime.fromtimestamp(int(timestamp) / 1_000_000, timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        event_time = datetime.now(timezone.utc).isoformat()
    msg = record.get('MESSAGE', '')
    if isinstance(msg, list):
        msg = '[non-text journal message]'
    msg = str(msg).replace('\x00', '')[:2048] or '[empty journal message]'
    ident = str(record.get('SYSLOG_IDENTIFIER') or record.get('_COMM') or 'journal')[:90]
    priority = str(record.get('PRIORITY', '6'))
    severity = 'high' if priority in ('0', '1', '2') else ('medium' if priority in ('3', '4') else 'info')
    return {
        'event_time': event_time,
        'event_type': 'linux.journal',
        'severity': severity,
        'message': msg,
        'payload': {
            'identifier': ident,
            'priority': priority,
            'hostname': str(record.get('_HOSTNAME', ''))[:128],
            'unit': str(record.get('_SYSTEMD_UNIT', ''))[:128],
        },
    }


def read_journal(cursor, limit):
    cmd = ['journalctl', '--no-pager', '--output=json', '--quiet', '--show-cursor', '-n', str(limit)]
    if cursor:
        cmd += ['--after-cursor', cursor]
    else:
        # At first startup, collect only recent entries; avoid huge historic backfill.
        cmd += ['--since', '10 minutes ago']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
    records = []
    for line in result.stdout.splitlines():
        if not line.startswith('{'):
            continue
        try:
            record = json.loads(line)
            if isinstance(record, dict) and record.get('__CURSOR'):
                records.append(record)
        except json.JSONDecodeError:
            continue
    # journalctl -n typically selects recent entries; sort by journal cursor order
    # as delivered. Persist the last successfully ingested cursor only.
    return records


def send(url, key, events, cafile):
    if not url.startswith('https://'):
        raise ValueError('Remote collection requires HTTPS')
    import ssl
    context = ssl.create_default_context(cafile=cafile if cafile else None)
    request = Request(
        url.rstrip('/') + '/telemetry/ingest',
        data=json.dumps({'events': events}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'X-Collector-Key': key},
        method='POST',
    )
    with urlopen(request, timeout=20, context=context) as response:
        result = json.load(response)
    if result.get('accepted') != len(events):
        raise ValueError('Server did not confirm full event count')
    return result


def write_cursor(path, cursor):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.cursor-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            file.write(cursor)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=os.getenv('PURPLEFORGE_API_URL', ''))
    parser.add_argument('--key-file', default=os.getenv('PURPLEFORGE_KEY_FILE', ''))
    parser.add_argument('--ca-file', default=os.getenv('PURPLEFORGE_CA_FILE', ''))
    parser.add_argument('--state-file', default=os.getenv('PURPLEFORGE_STATE_FILE', '/var/lib/purpleforge-journal/cursor'))
    parser.add_argument('--interval', type=int, default=10)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if not args.url.startswith('https://'):
        parser.error('PURPLEFORGE_API_URL must use HTTPS')
    key_file = Path(args.key_file)
    if not key_file.is_file():
        parser.error('Collector key file is missing')
    key = key_file.read_text(encoding='utf-8').strip()
    if not key:
        parser.error('Collector key is empty')
    state = Path(args.state_file)
    while True:
        try:
            cursor = state.read_text(encoding='utf-8').strip() if state.exists() else None
            records = read_journal(cursor, limit=50)
            if records:
                events = [to_event(record) for record in records]
                result = send(args.url, key, events, args.ca_file or None)
                write_cursor(state, records[-1]['__CURSOR'])
                print('accepted:', result['accepted'], flush=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError, URLError, HTTPError) as exc:
            print('collector retry; checkpoint unchanged:', type(exc).__name__, str(exc)[:200], file=sys.stderr, flush=True)
        if args.once:
            break
        time.sleep(max(2, args.interval))


if __name__ == '__main__':
    main()
