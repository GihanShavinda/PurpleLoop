from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, IPvAnyAddress

class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class RefreshInput(BaseModel):
    refresh_token: str

class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    is_active: bool
    role_name: str

class LabInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None

class LabPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None

class LabOutput(LabInput):
    model_config = ConfigDict(from_attributes=True)
    id: str

class AssetInput(BaseModel):
    lab_id: str
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: IPvAnyAddress | None = None
    mac_address: str | None = Field(default=None, pattern=r'(?i)^[0-9a-f]{2}(:[0-9a-f]{2}){5}$')
    operating_system: str | None = None
    asset_type: str = 'vm'
    environment: str = 'lab'
    criticality: Literal['low', 'medium', 'high', 'critical'] = 'medium'
    owner: str | None = None
    vm_name: str | None = None
    vmware_network: str | None = None
    monitoring_enabled: bool = False

class AssetPatch(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    ip_address: IPvAnyAddress | None = None
    mac_address: str | None = Field(default=None, pattern=r'(?i)^[0-9a-f]{2}(:[0-9a-f]{2}){5}$')
    operating_system: str | None = None
    asset_type: str | None = None
    environment: str | None = None
    criticality: Literal['low', 'medium', 'high', 'critical'] | None = None
    owner: str | None = None
    vm_name: str | None = None
    vmware_network: str | None = None
    monitoring_enabled: bool | None = None

class AssetOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lab_id: str
    hostname: str
    ip_address: str | None
    mac_address: str | None
    operating_system: str | None
    asset_type: str
    environment: str
    criticality: str
    owner: str | None
    vm_name: str | None
    vmware_network: str | None
    monitoring_enabled: bool
    created_at: datetime
    updated_at: datetime
