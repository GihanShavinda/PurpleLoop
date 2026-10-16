"""Authenticated, admin-only assurance dashboard. No exposed secrets or active probing."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from ..auth.security import require_roles
from ..config import get_settings
from .policy import evaluate_config, summarize

router = APIRouter(prefix="/assurance", tags=["P19 Security Assurance"])

@router.get("/posture")
def posture(_user=Depends(require_roles('Administrator'))):
    settings = get_settings()
    # Local configuration checks are advisory; endpoint deliberately avoids
    # returning configured origins, credentials, tokens, or environment files.
    checks = [c for c in evaluate_config(settings.allowed_origins, False, 'development') if c['id'] != 'debug_disabled']
    return {'generated_at':datetime.now(timezone.utc),'checks':checks,
            'summary':summarize(checks),
            'limitations':['Configuration-only checks are not a penetration test.',
              'Debug-mode configuration is not inspected by this endpoint.',
              'HTTPS and Caddy TLS policy require host-side verification.',
              'Review role authorization with an independent negative-access test.',
              'No VMware actions, scans, or response execution performed.']}
