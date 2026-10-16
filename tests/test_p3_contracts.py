"""Lightweight P3 validation tests, no live PostgreSQL necessary."""
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
import pytest
from backend.telemetry.routes import EventInput, BatchInput, SOURCE_TYPES

def test_timezone_required():
    with pytest.raises(ValidationError): EventInput(event_time=datetime(2026,1,1),event_type='x',message='x')

def test_future_rejected():
    with pytest.raises(ValidationError): EventInput(event_time=datetime.now(timezone.utc)+timedelta(days=1),event_type='x',message='x')

def test_batch_bounded():
    event=EventInput(event_time=datetime.now(timezone.utc),event_type='demo',message='test')
    with pytest.raises(ValidationError): BatchInput(events=[event]*101)

def test_source_types():
    assert {'sysmon','suricata','zeek','linux_journal','windows_event'} <= SOURCE_TYPES
