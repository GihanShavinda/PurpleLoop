"""P17 bounded, manual VMware cyber range readiness inspections."""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.security import current_user, require_roles
from ..models import Asset, User, AuditLog, TelemetryEvent, VmwareReadinessCheck
from .assessment import assess, ALLOWED_STATES
router=APIRouter(prefix='/vmware-range',tags=['P17 VMware Cyber Range - read only'])
WRITERS=('Administrator','Purple Team Engineer')

def parse_id(v):
    try: UUID(v)
    except (ValueError,TypeError): raise HTTPException(422,'Invalid asset identifier')

def export(x):
    return {'id':x.id,'asset_id':x.asset_id,'checked_at':x.checked_at,'vmx_path_label':x.vmx_path_label,'reported_power_state':x.reported_power_state,'reported_network':x.reported_network,'notes':x.notes,'observed_last_event':x.observed_last_event,'assessment':x.assessment_json}

class CheckRequest(BaseModel):
    asset_id: str
    reported_power_state: str
    reported_network: str = Field(default='',max_length=100)
    vmx_path_label: str = Field(default='',max_length=400)
    notes: str = Field(default='',max_length=1000)

@router.get('/assets')
def assets(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.scalars(select(Asset).order_by(Asset.hostname).limit(100)).all()
    return [{'id':x.id,'hostname':x.hostname,'ip_address':x.ip_address,'vmware_network':x.vmware_network,'vm_name':x.vm_name,'operating_system':x.operating_system} for x in rows]

@router.get('/checks')
def checks(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [export(x) for x in db.scalars(select(VmwareReadinessCheck).order_by(VmwareReadinessCheck.checked_at.desc()).limit(100)).all()]

@router.post('/checks',status_code=201)
def create(req:CheckRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(*WRITERS))):
    parse_id(req.asset_id)
    if req.reported_power_state not in ALLOWED_STATES: raise HTTPException(422,'Unknown power state')
    asset=db.get(Asset,req.asset_id)
    if asset is None:raise HTTPException(404,'Asset not found')
    # No shell, file or vmrun use. User-provided labels remain inert strings.
    now=datetime.now(timezone.utc)
    last=db.scalar(select(func.max(TelemetryEvent.received_at)).where(TelemetryEvent.asset_id==asset.id))
    result=assess(req.reported_power_state,asset.vmware_network,req.reported_network,last,now)
    x=VmwareReadinessCheck(asset_id=asset.id,checked_by=user.id,checked_at=now,vmx_path_label=req.vmx_path_label,reported_power_state=req.reported_power_state,reported_network=req.reported_network,notes=req.notes,observed_last_event=last,assessment_json=result)
    db.add(x);db.flush()
    db.add(AuditLog(actor_id=user.id,action='p17_manual_readiness_recorded',resource='vmware_readiness_check',resource_id=x.id))
    db.commit();db.refresh(x)
    return export(x)
