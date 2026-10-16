import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import get_settings
from .auth.routes import router as auth_router
from .api.routes import router as platform_router
from .auth.security import require_roles
from .integrations.services import checks
from .telemetry.routes import router as telemetry_router
from .detections.routes import router as detections_router
from .validation.routes import router as validation_router
from .incidents.routes import router as incidents_router
from .hunting.routes import router as hunting_router
from .intelligence.routes import router as intelligence_router
from .correlation.routes import router as correlation_router
from .analyst.routes import router as analyst_router

s=get_settings()
logging.basicConfig(level=getattr(logging,s.log_level.upper(),logging.INFO))
app=FastAPI(title='PurpleForge AI',version='0.10.0',description='P3 native telemetry collection for VMware lab. No attack execution.')
app.add_middleware(CORSMiddleware,allow_origins=s.allowed_origins,allow_credentials=True,allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type','X-Collector-Key'])
app.include_router(auth_router)
app.include_router(platform_router)
app.include_router(telemetry_router)
app.include_router(detections_router)
app.include_router(validation_router)
app.include_router(incidents_router)
app.include_router(hunting_router)
app.include_router(intelligence_router)
app.include_router(correlation_router)
app.include_router(analyst_router)

@app.get('/health', tags=['system'])
def health():
    return {'status':'ok','version':'P10'}

@app.get('/health/services',tags=['system'])
def services(user=Depends(require_roles('Administrator'))):
    result=checks()
    return JSONResponse(status_code=200 if all(x=='ok' for x in result.values()) else 503,content={'services':result})
