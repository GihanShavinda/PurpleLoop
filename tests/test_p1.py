import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.security import issue_token, decode_token, hash_password, verify_password, require_roles

client=TestClient(app)

def test_liveness():
    response=client.get('/health')
    assert response.status_code==200
    assert response.json()['status']=='ok'

def test_protected_requires_auth():
    assert client.get('/assets').status_code==401
    assert client.get('/labs').status_code==401
    assert client.get('/users').status_code==401

def test_password_hash_roundtrip():
    hashed=hash_password('StrongPassphrase-123')
    assert hashed!='StrongPassphrase-123'
    assert verify_password('StrongPassphrase-123',hashed)
    assert not verify_password('wrong',hashed)

def test_token_kind_and_signature():
    access=issue_token('fake-user','access',5)
    refresh=issue_token('fake-user','refresh',5)
    assert decode_token(access,'access')['sub']=='fake-user'
    from fastapi import HTTPException
    with pytest.raises(HTTPException):decode_token(refresh,'access')
    with pytest.raises(HTTPException):decode_token(access+'bad','access')

def test_openapi():
    doc=client.get('/openapi.json')
    assert doc.status_code==200
    for route in ['/auth/login','/auth/refresh','/assets','/labs','/health/services']:
        assert route in doc.json()['paths']

@pytest.mark.skipif(os.getenv('PURPLEFORGE_INTEGRATION')!='1',reason='Requires running services and seeded P1 database; set PURPLEFORGE_INTEGRATION=1')
def test_native_services():
    from backend.integrations.services import checks
    assert checks()=={'postgresql':'ok','redis':'ok','neo4j':'ok'}
