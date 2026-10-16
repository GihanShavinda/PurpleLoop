"""Bounded per-asset time-bucket anomaly features. No raw payloads or executable model files."""
from collections import Counter
from datetime import datetime, timezone, timedelta
import math

FEATURE_NAMES = ("volume", "warnings", "errors", "distinct_types")

def bucketize(rows, start: datetime, end: datetime, minutes: int):
    """Build zero-filled buckets; rows=(aware datetime,event_type,severity)."""
    if start.tzinfo is None or end.tzinfo is None or not 5 <= minutes <= 60 or start >= end:
        raise ValueError('invalid time range or bucket size')
    count = math.ceil((end-start).total_seconds()/(minutes*60))
    if count > 288: raise ValueError('too many buckets')
    buckets = [dict(bucket_start=start+timedelta(minutes=i*minutes), volume=0, warnings=0, errors=0, distinct_types=0) for i in range(count)]
    types = [set() for _ in buckets]
    for moment, event_type, severity in rows:
        if moment.tzinfo is None: moment=moment.replace(tzinfo=timezone.utc)
        index=int((moment-start).total_seconds()//(minutes*60))
        if not 0 <= index < count: continue
        b=buckets[index];b['volume']+=1
        if severity.lower() in ('warning','warn','medium','high','critical'): b['warnings']+=1
        if severity.lower() in ('error','high','critical'): b['errors']+=1
        types[index].add(event_type)
    for i,b in enumerate(buckets):b['distinct_types']=len(types[i])
    return buckets

def evaluate_buckets(buckets, contamination=0.08):
    """Isolation Forest scores for historical buckets, no future claims or malware assertions."""
    if len(buckets)<12: raise ValueError('At least 12 time buckets are required')
    if not 0.01 <= contamination <= 0.2: raise ValueError('contamination outside 1-20 percent')
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError as exc:
        raise RuntimeError('scikit-learn not installed; pip install scikit-learn') from exc
    data=[[float(b[key]) for key in FEATURE_NAMES] for b in buckets]
    # Collapse to a pure volume feature when the other channels are constant.
    model=IsolationForest(n_estimators=100,contamination=contamination,random_state=42,n_jobs=1)
    predicted=model.fit_predict(data)
    raw=model.decision_function(data)
    means={name:sum(b[name] for b in buckets)/len(buckets) for name in FEATURE_NAMES}
    result=[]
    for i,(bucket,flag,margin) in enumerate(zip(buckets,predicted,raw)):
        if flag != -1: continue
        deltas={name:round(float(bucket[name]-means[name]),2) for name in FEATURE_NAMES}
        main=max(FEATURE_NAMES,key=lambda name:abs(deltas[name]))
        result.append({'bucket_start':bucket['bucket_start'],'anomaly_score':round(max(0.,float(-margin)),6),
                       'event_count':bucket['volume'], 'explanation':{'principal_feature':main,
                       'observed':{name:bucket[name] for name in FEATURE_NAMES},
                       'baseline_mean':{name:round(means[name],2) for name in FEATURE_NAMES},
                       'difference_from_mean':deltas,
                       'warning':'Statistical outlier, not proof of malicious behavior'}})
    return result
