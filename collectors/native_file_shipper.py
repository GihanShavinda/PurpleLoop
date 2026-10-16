"""Native JSONL log shipper; run in a Python venv on Windows or Linux.

Input format: one JSON event per line with event_time (ISO 8601 with timezone),
 event_type, severity, message, payload. Uses a persistent byte offset and
 retries without advancing checkpoint on failed submission.
"""
import json
import os
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

API=os.environ.get('PURPLEFORGE_API_URL','http://127.0.0.1:8000').rstrip('/')
KEY=os.environ.get('PURPLEFORGE_COLLECTOR_KEY','')
FILE=Path(os.environ.get('PURPLEFORGE_LOG_FILE','events.jsonl'))
OFFSET=Path(os.environ.get('PURPLEFORGE_OFFSET_FILE',str(FILE)+'.offset'))
INTERVAL=max(1,int(os.environ.get('PURPLEFORGE_POLL_SECONDS','5')))

def send(events):
    data=json.dumps({'events':events}).encode()
    request=Request(API+'/telemetry/ingest',data=data,method='POST',headers={'Content-Type':'application/json','X-Collector-Key':KEY})
    with urlopen(request,timeout=15) as response:
        return json.load(response)

def run_once():
    if not FILE.exists():return
    old=int(OFFSET.read_text()) if OFFSET.exists() else 0
    if FILE.stat().st_size<old:old=0
    with FILE.open('rb') as handle:
        handle.seek(old)
        events=[]; last=old
        while len(events)<50:
            line=handle.readline()
            if not line or not line.endswith(b'\n'):break
            last=handle.tell()
            try:events.append(json.loads(line))
            except (ValueError,UnicodeDecodeError) as exc:
                print('Invalid JSON line; stopping without advancing cursor:',exc,file=sys.stderr)
                return
        if not events:return
        send(events)
        OFFSET.write_text(str(last))
        print(f'Accepted {len(events)} event(s)')

if __name__=='__main__':
    if not KEY:raise SystemExit('Set PURPLEFORGE_COLLECTOR_KEY securely in the collector process environment')
    if not API.startswith('https://') and not (API.startswith('http://127.0.0.1:') or API.startswith('http://localhost:')):
        raise SystemExit('Remote ingestion must use HTTPS; configure a TLS reverse proxy on the Windows host.')
    print('Native collector started; source file:',FILE)
    while True:
        try:run_once()
        except (URLError,HTTPError,OSError,ValueError) as exc:print('Ingestion deferred:',exc,file=sys.stderr)
        time.sleep(INTERVAL)
