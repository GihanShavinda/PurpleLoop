from datetime import datetime, timezone, timedelta
import pytest
from backend.hunting.query import validate_window, escaped_contains, normalize_ioc

def test_window_bounds():
    end=datetime.now(timezone.utc)
    assert validate_window(end-timedelta(hours=2),end)[1]==end
    with pytest.raises(ValueError):validate_window(end-timedelta(days=8),end)
    with pytest.raises(ValueError):validate_window(end,end)

def test_escape_wildcards():
    assert escaped_contains('a%b_c')==r'%a\%b\_c%'

def test_ioc_validation():
    assert normalize_ioc('ip','192.168.37.20')=='192.168.37.20'
    assert normalize_ioc('domain','Example.COM')=='example.com'
    with pytest.raises(ValueError):normalize_ioc('ip','invalid')
    with pytest.raises(ValueError):normalize_ioc('hash','not-a-hash')
