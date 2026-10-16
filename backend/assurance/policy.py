"""Read-only configuration checks; never return secrets or raw configuration values."""
from urllib.parse import urlparse

def evaluate_config(allowed_origins, debug: bool, environment: str = 'development'):
    origins = list(allowed_origins or [])
    results = [
        {"id": "cors_no_wildcard", "passed": bool(origins) and all(x != '*' for x in origins), "reason": "Explicit CORS origins required"},
        {"id": "cors_no_null", "passed": all(x.lower() != 'null' for x in origins), "reason": "Null origin must not be trusted"},
        {"id": "cors_valid_urls", "passed": all(urlparse(x).scheme in ('http','https') and bool(urlparse(x).netloc) for x in origins), "reason": "Origin list must contain valid HTTP(S) origins"},
        {"id": "debug_disabled", "passed": not debug, "reason": "Debug responses must be disabled"},
    ]
    if environment.lower() == 'production':
        results.append({"id":"production_tls_origins", "passed":all(x.startswith('https://') for x in origins),"reason":"Production cross-origin access must use HTTPS"})
    return results

def summarize(checks):
    return {'passed':sum(bool(c['passed']) for c in checks),'total':len(checks),'attention_required':sum(not bool(c['passed']) for c in checks)}
