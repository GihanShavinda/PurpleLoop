"""Portable source contract checks; full API auth tests must run against local DB."""
from pathlib import Path

def test_assurance_router_is_admin_only():
    text=Path('backend/assurance/routes.py').read_text(encoding='utf-8')
    assert "require_roles('Administrator')" in text
    assert 'get_settings()' in text
    assert 'password' not in text.lower()

def test_p19_keeps_existing_api_routers():
    text=Path('backend/main.py').read_text(encoding='utf-8')
    for router in ('telemetry_router','detections_router','validation_router','incidents_router','anomaly_router','operations_router','assurance_router'):
        assert f'app.include_router({router})' in text
