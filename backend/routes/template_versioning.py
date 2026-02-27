"""
Template Versioning & A/B Testing API Routes
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from shared import db, get_admin_user
from services.template_versioning import (
    create_template_version,
    get_template_versions,
    activate_template_version,
    create_ab_test,
    get_ab_test_variant,
    record_ab_conversion,
    get_ab_test_results,
    get_active_ab_tests,
    end_ab_test,
    TemplateVersionStatus
)
from services.audit_log import log_admin_action, AuditAction

router = APIRouter(prefix="/template-versioning", tags=["Template Versioning"])

# ==================== VERSION MANAGEMENT ====================

class CreateVersionRequest(BaseModel):
    template_id: str
    template_type: str
    content: Dict[str, Any]
    notes: Optional[str] = None

class ActivateVersionRequest(BaseModel):
    version_id: str

@router.post("/versions")
async def create_version(
    request: CreateVersionRequest,
    admin: dict = Depends(get_admin_user)
):
    """Create a new template version"""
    admin_id = str(admin.get("id") or admin.get("_id"))
    
    version = await create_template_version(
        db,
        template_id=request.template_id,
        template_type=request.template_type,
        content=request.content,
        created_by=admin_id,
        notes=request.notes
    )
    
    # Log action
    await log_admin_action(
        db,
        admin_id=admin_id,
        admin_email=admin.get("email", ""),
        action=AuditAction.TEMPLATE_CREATE,
        resource_type="template_version",
        resource_id=version.get("id"),
        details={"template_id": request.template_id, "version": version.get("version")}
    )
    
    return version

@router.get("/versions/{template_id}")
async def list_versions(
    template_id: str,
    include_archived: bool = False,
    admin: dict = Depends(get_admin_user)
):
    """Get all versions of a template"""
    versions = await get_template_versions(db, template_id, include_archived)
    return {"versions": versions, "count": len(versions)}

@router.post("/versions/activate")
async def activate_version(
    request: ActivateVersionRequest,
    admin: dict = Depends(get_admin_user)
):
    """Activate a specific template version"""
    admin_id = str(admin.get("id") or admin.get("_id"))
    
    success = await activate_template_version(db, request.version_id, admin_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Log action
    await log_admin_action(
        db,
        admin_id=admin_id,
        admin_email=admin.get("email", ""),
        action=AuditAction.TEMPLATE_ACTIVATE,
        resource_type="template_version",
        resource_id=request.version_id
    )
    
    return {"success": True, "message": "Version activated"}

# ==================== A/B TESTING ====================

class CreateABTestRequest(BaseModel):
    name: str
    template_type: str
    variant_a_id: str
    variant_b_id: str
    traffic_split: float = 0.5

class EndABTestRequest(BaseModel):
    test_id: str
    winner_id: str

@router.post("/ab-tests")
async def create_test(
    request: CreateABTestRequest,
    admin: dict = Depends(get_admin_user)
):
    """Create a new A/B test"""
    admin_id = str(admin.get("id") or admin.get("_id"))
    
    test = await create_ab_test(
        db,
        name=request.name,
        template_type=request.template_type,
        variant_a_id=request.variant_a_id,
        variant_b_id=request.variant_b_id,
        traffic_split=request.traffic_split,
        created_by=admin_id
    )
    
    # Log action
    await log_admin_action(
        db,
        admin_id=admin_id,
        admin_email=admin.get("email", ""),
        action=AuditAction.CONFIG_UPDATE,
        resource_type="ab_test",
        resource_id=test.get("id"),
        details={"name": request.name, "variants": [request.variant_a_id, request.variant_b_id]}
    )
    
    return test

@router.get("/ab-tests")
async def list_tests(admin: dict = Depends(get_admin_user)):
    """Get all active A/B tests"""
    tests = await get_active_ab_tests(db)
    return {"tests": tests, "count": len(tests)}

@router.get("/ab-tests/{test_id}/results")
async def get_results(
    test_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Get A/B test results with winner analysis"""
    results = await get_ab_test_results(db, test_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return results

@router.post("/ab-tests/end")
async def end_test(
    request: EndABTestRequest,
    admin: dict = Depends(get_admin_user)
):
    """End an A/B test and activate the winner"""
    admin_id = str(admin.get("id") or admin.get("_id"))
    
    success = await end_ab_test(db, request.test_id, request.winner_id, admin_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Log action
    await log_admin_action(
        db,
        admin_id=admin_id,
        admin_email=admin.get("email", ""),
        action=AuditAction.CONFIG_UPDATE,
        resource_type="ab_test",
        resource_id=request.test_id,
        details={"action": "ended", "winner_id": request.winner_id}
    )
    
    return {"success": True, "message": "Test ended and winner activated"}

# ==================== PUBLIC VARIANT ENDPOINT ====================

@router.get("/variant/{test_id}")
async def get_variant(test_id: str, user_id: str):
    """Get the assigned variant for a user (public endpoint)"""
    variant = await get_ab_test_variant(db, test_id, user_id)
    
    if not variant:
        raise HTTPException(status_code=404, detail="Test not found or inactive")
    
    return variant

@router.post("/conversion/{test_id}")
async def track_conversion(test_id: str, user_id: str):
    """Track a conversion for an A/B test (public endpoint)"""
    success = await record_ab_conversion(db, test_id, user_id)
    return {"success": success}
