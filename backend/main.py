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
from .soar.routes import router as soar_router
from .response.routes import router as response_router
from .simulation.routes import router as simulation_router
from .coverage.routes import router as coverage_router
from .anomaly.routes import router as anomaly_router
from .investigation.routes import router as investigation_router
from .vmware_range.routes import router as vmware_range_router
from .operations.routes import router as operations_router
from .assurance.routes import router as assurance_router
from .assurance.headers import apply_security_headers
from .release.routes import router as release_router

s=get_settings()
logging.basicConfig(level=getattr(logging,s.log_level.upper(),logging.INFO))
app=FastAPI(title='PurpleForge AI',version='0.20.0',description='P3 native telemetry collection for VMware lab. No attack execution.')
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
app.include_router(soar_router)
app.include_router(response_router)
app.include_router(simulation_router)
app.include_router(coverage_router)
app.include_router(anomaly_router)
app.include_router(investigation_router)
app.include_router(vmware_range_router)
app.include_router(operations_router)
app.include_router(assurance_router)
app.include_router(release_router)

@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    apply_security_headers(response.headers, request.url.scheme)
    return response

@app.get('/health', tags=['system'])
def health():
    return {'status':'ok','version':'P20'}

@app.get('/health/services',tags=['system'])
def services(user=Depends(require_roles('Administrator'))):
    result=checks()
    return JSONResponse(status_code=200 if all(x=='ok' for x in result.values()) else 503,content={'services':result})
