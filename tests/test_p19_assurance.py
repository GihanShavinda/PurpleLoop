from backend.assurance.headers import apply_security_headers
from backend.assurance.policy import evaluate_config, summarize

def test_defensive_headers_and_no_hsts_over_http():
    headers={};apply_security_headers(headers,'http')
    assert headers['X-Content-Type-Options']=='nosniff'
    assert headers['X-Frame-Options']=='DENY'
    assert 'Strict-Transport-Security' not in headers

def test_hsts_on_https():
    headers={};apply_security_headers(headers,'https')
    assert 'Strict-Transport-Security' in headers

def test_wildcard_cors_fails():
    checks=evaluate_config(['*'],False)
    assert not next(c for c in checks if c['id']=='cors_no_wildcard')['passed']

def test_allowed_local_origin():
    checks=evaluate_config(['http://localhost:4200'],False)
    assert summarize(checks)['attention_required']==0

def test_prod_requires_tls():
    checks=evaluate_config(['http://localhost:4200'],False,'production')
    assert not next(c for c in checks if c['id']=='production_tls_origins')['passed']
