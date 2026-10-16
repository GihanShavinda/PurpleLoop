"""P2 API schema contract smoke tests; no live PostgreSQL required."""
from backend.schemas import LabPatch, AssetInput
from pydantic import ValidationError
import pytest


def test_lab_patch_name_limits():
    assert LabPatch(name='Renamed Lab').name == 'Renamed Lab'
    with pytest.raises(ValidationError):
        LabPatch(name='')


def test_vmware_asset_accepts_p2_types():
    data = AssetInput(lab_id='sample-id', hostname='kali-01', asset_type='Attacker', vmware_network='VMnet2', ip_address='192.168.56.3')
    assert data.asset_type == 'Attacker'
    assert str(data.ip_address) == '192.168.56.3'


def test_invalid_mac_rejected():
    with pytest.raises(ValidationError):
        AssetInput(lab_id='sample-id',hostname='target-01',mac_address='not-a-mac')
