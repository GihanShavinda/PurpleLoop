#!/usr/bin/env python3
"""P3.4 native Suricata EVE / Zeek JSON-lines -> PurpleForge telemetry.

One source key per process. No packet capture or promiscuous-mode changes.
Requires Python 3.10+; standard library only.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import time
from urllib.request import Request, urlopen

MAX_LINE = 120_000
MAX_BATCH = 30


def compact(value, limit=180):
    return str(value or '').replace('\x00', '')[:limit]


def event_time(data):
    raw = data.get('timestamp') or data.get('ts')
    try:
        if isinstance(raw, (int, float)):
            stamp = datetime.fromtimestamp(raw, tz=timezone.utc)
        else:
            stamp = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return datetime.now(timezone.utc).isoformat()


def normalize(kind, record):
    if not isinstance(record, dict):
        return None
    if kind == 'suricata':
        subtype = compact(record.get('event_type', 'unknown'), 50)
        alert = record.get('alert') if isinstance(record.get('alert'), dict) else {}
        sig = compact(alert.get('signature'), 360)
        msg = sig or 'Suricata ' + subtype
        sev = 'high' if alert.get('severity') == 1 else ('medium' if alert.get('severity') == 2 else 'info')
        event_type = 'suricata.' + subtype
        payload = {k: compact(record.get(k)) for k in ('src_ip','dest_ip','proto','app_proto','flow_id') if record.get(k) is not None}
        for k in ('src_port','dest_port'):
            if isinstance(record.get(k), int): payload[k] = record[k]
        if alert:
            payload['signature_id'] = alert.get('signature_id') if isinstance(alert.get('signature_id'),int) else None
            payload['category'] = compact(alert.get('category'))
    else:
        # Zeek JSON logs are selected by their input file; _path is optional.
        subtype = compact(record.get('_path') or record.get('path') or 'json', 50)
        event_type = 'zeek.' + subtype
        msg = 'Zeek ' + subtype + ' event'
        sev = 'info'
        payload = {k: compact(record.get(k), 300) for k in ('uid','id.orig_h','id.resp_h','proto','service','query','host','note') if record.get(k) is not None}
        for k in ('id.orig_p','id.resp_p'):
            if isinstance(record.get(k), int): payload[k] = record[k]
    return {'event_time':event_time(record),'event_type':event_type[:120], 'severity':sev,
            'message':msg[:2048], 'payload':payload}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.p34-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(state,f)
            f.flush(); os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def load_state(path, stat):
    if path.exists():
        try:
            state=json.loads(path.read_text(encoding='utf-8'))
            if state['inode'] == stat.st_ino and stat.st_size >= state['offset']:
                return state
        except (OSError, ValueError, KeyError, TypeError):
            pass
    # First run skips historical data; after rotation also skips the new file's
    # current contents. Documented tradeoff: events may be missed during rotation.
    return {'inode':stat.st_ino, 'offset':stat.st_size}


def read_batch(path, state):
    out=[]
    with path.open('rb') as f:
        f.seek(state['offset'])
        while len(out) < MAX_BATCH:
            start=f.tell()
            line=f.readline(MAX_LINE + 1)
            if not line: break
            if len(line)>MAX_LINE:
                raise ValueError('Overlong log line at byte '+str(start))
            if not line.endswith(b'\n'):
                break   # do not checkpoint partially written JSON lines
            out.append((f.tell(),line))
    return out


def post(url,key,ca,events):
    body=json.dumps({'events':events},separators=(',',':')).encode('utf-8')
    if len(body)>240_000: raise ValueError('Batch exceeds safe size')
    ctx=ssl.create_default_context(cafile=ca)
    req=Request(url.rstrip('/')+'/telemetry/ingest',data=body,
                headers={'Content-Type':'application/json','X-Collector-Key':key},method='POST')
    with urlopen(req,timeout=20,context=ctx) as resp:
        result=json.load(resp)
    if result.get('accepted')!=len(events): raise ValueError('Unexpected accepted count')
    return result['accepted']


def run_once(args,key):
    path=Path(args.file)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    stat=path.stat()
    state_path=Path(args.state)
    state=load_state(state_path,stat)
    if not state_path.exists() or state['inode']!=stat.st_ino or state['offset']==stat.st_size and stat.st_size < 1:
        save_state(state_path,state)
    batch=read_batch(path,state)
    if not batch:
        save_state(state_path,state)
        return 0
    normalized=[]; last=state['offset']
    for offset,line in batch:
        try:
            raw=json.loads(line)
            event=normalize(args.kind,raw)
        except (UnicodeError, ValueError):
            event=None
        if event is not None: normalized.append(event)
        last=offset
    if normalized:
        accepted=post(args.url,key,args.ca,normalized)
    else: accepted=0
    save_state(state_path,{'inode':stat.st_ino,'offset':last})
    return accepted


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--kind',required=True,choices=('suricata','zeek'))
    p.add_argument('--file',required=True)
    p.add_argument('--state',required=True)
    p.add_argument('--key-file',required=True)
    p.add_argument('--ca',required=True)
    p.add_argument('--url',required=True)
    p.add_argument('--once',action='store_true')
    p.add_argument('--interval',type=int,default=10)
    args=p.parse_args()
    if not args.url.startswith('https://'):p.error('HTTPS required')
    key=Path(args.key_file).read_text(encoding='utf-8').strip()
    if not key:p.error('Empty collector key')
    while True:
        try:
            accepted=run_once(args,key)
            if accepted:print('accepted:',accepted,flush=True)
        except Exception as exc:
            print('retry; checkpoint unchanged:',type(exc).__name__,str(exc)[:150],file=sys.stderr,flush=True)
        if args.once:break
        time.sleep(max(2,args.interval))

if __name__=='__main__':main()
