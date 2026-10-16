from datetime import datetime, timezone, timedelta
import pytest
from backend.anomaly.engine import bucketize,evaluate_buckets

def test_bucketize_zero_fills_and_counts():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[(start+timedelta(minutes=1),'linux.journal','info'),(start+timedelta(minutes=7),'sysmon.1','high')]
    buckets=bucketize(rows,start,start+timedelta(minutes=60),5)
    assert len(buckets)==12 and buckets[0]['volume']==1 and buckets[1]['errors']==1 and buckets[2]['volume']==0

def test_bucket_range_validation():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    with pytest.raises(ValueError):bucketize([],start,start+timedelta(hours=25),5)
    with pytest.raises(ValueError):bucketize([],start,start,15)

def test_deterministic_outlier_output():
    pytest.importorskip('sklearn')
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    bins=[{'bucket_start':start+timedelta(minutes=i*15),'volume':1+(50 if i==10 else 0),'warnings':0,'errors':0,'distinct_types':1} for i in range(24)]
    assert evaluate_buckets(bins,.08)==evaluate_buckets(bins,.08)
    assert all('principal_feature' in row['explanation'] for row in evaluate_buckets(bins,.08))

def test_insufficient_buckets():
    with pytest.raises(ValueError): evaluate_buckets([],0.08)
