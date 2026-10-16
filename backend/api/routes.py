from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import User, Role, Lab, Asset, AuditLog
from ..schemas import LabInput, LabOutput, LabPatch, AssetInput, AssetPatch, AssetOutput
from ..auth.security import current_user, require_roles

router = APIRouter(tags=['platform'])
MANAGERS=('Administrator','Purple Team Engineer')
EDITORS=('Administrator','Purple Team Engineer','Detection Engineer')

def audit(db, user, action, resource, resource_id):
    db.add(AuditLog(actor_id=user.id,action=action,resource=resource,resource_id=resource_id))

def save(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Duplicate or invalid reference')

@router.get('/users')
def list_users(db:Session=Depends(get_db), user:User=Depends(require_roles('Administrator'))):
    rows = db.scalars(select(User).order_by(User.email).limit(200)).all()
    return [{'id':u.id,'email':u.email,'role_name':u.role.name,'is_active':u.is_active} for u in rows]

@router.get('/users/{user_id}')
def get_user(user_id:str, db:Session=Depends(get_db), actor:User=Depends(current_user)):
    if actor.id != user_id and actor.role.name != 'Administrator':
        raise HTTPException(403,'Forbidden')
    u = db.get(User,user_id)
    if not u: raise HTTPException(404,'User not found')
    return {'id':u.id,'email':u.email,'role_name':u.role.name,'is_active':u.is_active}

@router.patch('/users/{user_id}/role')
def change_role(user_id:str, payload:dict, db:Session=Depends(get_db), actor:User=Depends(require_roles('Administrator'))):
    u = db.get(User,user_id)
    role = db.scalar(select(Role).where(Role.name == payload.get('role_name')))
    if not u or not role: raise HTTPException(404,'User or role not found')
    if u.id == actor.id and role.name != 'Administrator':
        raise HTTPException(400,'Cannot remove your own admin role')
    u.role_id = role.id
    audit(db,actor,'role_changed','user',u.id)
    save(db)
    return {'id':u.id,'role_name':role.name}

@router.get('/labs',response_model=list[LabOutput])
def labs(db:Session=Depends(get_db), user:User=Depends(current_user)):
    return db.scalars(select(Lab).order_by(Lab.name).limit(200)).all()

@router.post('/labs',response_model=LabOutput,status_code=201)
def create_lab(payload:LabInput,db:Session=Depends(get_db),user:User=Depends(require_roles(*MANAGERS))):
    obj = Lab(**payload.model_dump())
    db.add(obj)
    db.flush()
    audit(db,user,'created','lab',obj.id)
    save(db)
    return obj

@router.get('/labs/{lab_id}',response_model=LabOutput)
def get_lab(lab_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    obj=db.get(Lab,lab_id)
    if not obj:raise HTTPException(404,'Lab not found')
    return obj

@router.patch('/labs/{lab_id}',response_model=LabOutput)
def update_lab(lab_id:str,payload:LabPatch,db:Session=Depends(get_db),user:User=Depends(require_roles(*MANAGERS))):
    lab=db.get(Lab,lab_id)
    if not lab: raise HTTPException(404,'Lab not found')
    for key,value in payload.model_dump(exclude_unset=True).items():
        setattr(lab,key,value)
    audit(db,user,'updated','lab',lab_id)
    save(db)
    db.refresh(lab)
    return lab

@router.delete('/labs/{lab_id}',status_code=204)
def delete_lab(lab_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles('Administrator'))):
    obj=db.get(Lab,lab_id)
    if not obj:raise HTTPException(404,'Lab not found')
    if db.scalar(select(Asset.id).where(Asset.lab_id==lab_id).limit(1)):
        raise HTTPException(409,'Remove lab assets first')
    db.delete(obj)
    audit(db,user,'deleted','lab',lab_id)
    save(db)

@router.get('/inventory/summary')
def inventory_summary(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return {
        'labs':db.scalar(select(func.count(Lab.id))) or 0,
        'assets':db.scalar(select(func.count(Asset.id))) or 0,
        'monitored':db.scalar(select(func.count(Asset.id)).where(Asset.monitoring_enabled.is_(True))) or 0,
        'critical':db.scalar(select(func.count(Asset.id)).where(Asset.criticality=='critical')) or 0,
    }

@router.get('/assets',response_model=list[AssetOutput])
def assets(lab_id:str|None=None,search:str|None=Query(None,max_length=120),asset_type:str|None=None,criticality:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Asset)
    if lab_id:q=q.where(Asset.lab_id==lab_id)
    if search:
        term=f'%{search.strip()}%'
        q=q.where(or_(Asset.hostname.ilike(term),Asset.ip_address.ilike(term),Asset.vm_name.ilike(term)))
    if asset_type:q=q.where(Asset.asset_type==asset_type)
    if criticality:q=q.where(Asset.criticality==criticality)
    q=q.order_by(Asset.created_at.desc()).offset(offset).limit(limit)
    return db.scalars(q).all()

@router.post('/assets',response_model=AssetOutput,status_code=201)
def create_asset(payload:AssetInput,db:Session=Depends(get_db),user:User=Depends(require_roles(*EDITORS))):
    if not db.get(Lab,payload.lab_id):raise HTTPException(404,'Lab not found')
    values=payload.model_dump()
    if values['ip_address'] is not None:values['ip_address']=str(values['ip_address'])
    obj=Asset(**values)
    db.add(obj)
    db.flush()
    audit(db,user,'created','asset',obj.id)
    save(db)
    return obj

@router.get('/assets/{asset_id}',response_model=AssetOutput)
def get_asset(asset_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    obj=db.get(Asset,asset_id)
    if not obj:raise HTTPException(404,'Asset not found')
    return obj

@router.patch('/assets/{asset_id}',response_model=AssetOutput)
def edit_asset(asset_id:str,payload:AssetPatch,db:Session=Depends(get_db),user:User=Depends(require_roles(*EDITORS))):
    obj=db.get(Asset,asset_id)
    if not obj:raise HTTPException(404,'Asset not found')
    for key,val in payload.model_dump(exclude_unset=True).items():
        setattr(obj,key,str(val) if key=='ip_address' and val is not None else val)
    audit(db,user,'updated','asset',obj.id)
    save(db)
    db.refresh(obj)
    return obj

@router.delete('/assets/{asset_id}',status_code=204)
def remove_asset(asset_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles(*MANAGERS))):
    obj=db.get(Asset,asset_id)
    if not obj:raise HTTPException(404,'Asset not found')
    db.delete(obj)
    audit(db,user,'deleted','asset',asset_id)
    save(db)
