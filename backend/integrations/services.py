from sqlalchemy import text
from redis import Redis
from neo4j import GraphDatabase
from ..database import engine
from ..config import get_settings

def checks():
    s=get_settings()
    statuses={}
    try:
        with engine.connect() as c:c.execute(text('SELECT 1'))
        statuses['postgresql']='ok'
    except Exception:
        statuses['postgresql']='unavailable'
    try:
        client=Redis.from_url(s.redis_url,socket_connect_timeout=2,socket_timeout=2)
        try: client.ping();statuses['redis']='ok'
        finally:client.close()
    except Exception:
        statuses['redis']='unavailable'
    try:
        with GraphDatabase.driver(s.neo4j_uri,auth=(s.neo4j_username,s.neo4j_password),connection_timeout=2) as driver:
            driver.verify_connectivity()
            statuses['neo4j']='ok'
    except Exception:
        statuses['neo4j']='unavailable'
    return statuses
