"""
Template Versioning & A/B Testing Service
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
import random

class TemplateVersionStatus:
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    TESTING = "testing"  # For A/B testing

async def create_template_version(
    db,
    template_id: str,
    template_type: str,
    content: Dict[str, Any],
    created_by: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new version of a template"""
    # Get current version number
    existing = await db.template_versions.find_one(
        {"template_id": template_id},
        sort=[("version", -1)]
    )
    
    version = (existing.get("version", 0) if existing else 0) + 1
    
    version_doc = {
        "template_id": template_id,
        "template_type": template_type,
        "version": version,
        "content": content,
        "status": TemplateVersionStatus.DRAFT,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc),
        "notes": notes,
        "metrics": {
            "impressions": 0,
            "selections": 0,
            "conversions": 0
        }
    }
    
    result = await db.template_versions.insert_one(version_doc)
    version_doc["id"] = str(result.inserted_id)
    del version_doc["_id"]
    
    return version_doc

async def get_template_versions(
    db,
    template_id: str,
    include_archived: bool = False
) -> List[Dict[str, Any]]:
    """Get all versions of a template"""
    query = {"template_id": template_id}
    if not include_archived:
        query["status"] = {"$ne": TemplateVersionStatus.ARCHIVED}
    
    versions = await db.template_versions.find(query).sort("version", -1).to_list(100)
    
    for v in versions:
        v["id"] = str(v.pop("_id"))
        v["created_at"] = v["created_at"].isoformat()
    
    return versions

async def activate_template_version(
    db,
    version_id: str,
    activated_by: str
) -> bool:
    """Activate a specific version (deactivates others)"""
    version = await db.template_versions.find_one({"_id": ObjectId(version_id)})
    if not version:
        return False
    
    # Deactivate all other active versions of this template
    await db.template_versions.update_many(
        {"template_id": version["template_id"], "status": TemplateVersionStatus.ACTIVE},
        {"$set": {"status": TemplateVersionStatus.ARCHIVED}}
    )
    
    # Activate this version
    await db.template_versions.update_one(
        {"_id": ObjectId(version_id)},
        {"$set": {
            "status": TemplateVersionStatus.ACTIVE,
            "activated_at": datetime.now(timezone.utc),
            "activated_by": activated_by
        }}
    )
    
    return True

# ==================== A/B Testing ====================

async def create_ab_test(
    db,
    name: str,
    template_type: str,
    variant_a_id: str,
    variant_b_id: str,
    traffic_split: float = 0.5,  # 50% to each
    created_by: str = None
) -> Dict[str, Any]:
    """Create a new A/B test"""
    test_doc = {
        "name": name,
        "template_type": template_type,
        "variant_a_id": variant_a_id,
        "variant_b_id": variant_b_id,
        "traffic_split": traffic_split,
        "status": "active",
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc),
        "metrics": {
            "variant_a": {"impressions": 0, "conversions": 0},
            "variant_b": {"impressions": 0, "conversions": 0}
        }
    }
    
    result = await db.ab_tests.insert_one(test_doc)
    test_doc["id"] = str(result.inserted_id)
    del test_doc["_id"]
    
    # Mark versions as testing
    await db.template_versions.update_many(
        {"_id": {"$in": [ObjectId(variant_a_id), ObjectId(variant_b_id)]}},
        {"$set": {"status": TemplateVersionStatus.TESTING}}
    )
    
    return test_doc

async def get_ab_test_variant(
    db,
    test_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Get the variant for a user (consistent per user)"""
    test = await db.ab_tests.find_one({"_id": ObjectId(test_id), "status": "active"})
    if not test:
        return None
    
    # Use user_id hash for consistent assignment
    user_hash = hash(f"{test_id}:{user_id}") % 100
    use_variant_a = user_hash < (test["traffic_split"] * 100)
    
    variant_id = test["variant_a_id"] if use_variant_a else test["variant_b_id"]
    variant_key = "variant_a" if use_variant_a else "variant_b"
    
    # Record impression
    await db.ab_tests.update_one(
        {"_id": ObjectId(test_id)},
        {"$inc": {f"metrics.{variant_key}.impressions": 1}}
    )
    
    # Get variant content
    version = await db.template_versions.find_one({"_id": ObjectId(variant_id)})
    if version:
        version["id"] = str(version.pop("_id"))
        version["variant"] = variant_key
    
    return version

async def record_ab_conversion(
    db,
    test_id: str,
    user_id: str
) -> bool:
    """Record a conversion for an A/B test"""
    test = await db.ab_tests.find_one({"_id": ObjectId(test_id)})
    if not test:
        return False
    
    # Determine which variant the user saw
    user_hash = hash(f"{test_id}:{user_id}") % 100
    variant_key = "variant_a" if user_hash < (test["traffic_split"] * 100) else "variant_b"
    
    await db.ab_tests.update_one(
        {"_id": ObjectId(test_id)},
        {"$inc": {f"metrics.{variant_key}.conversions": 1}}
    )
    
    return True

async def get_ab_test_results(
    db,
    test_id: str
) -> Dict[str, Any]:
    """Get A/B test results with statistical analysis"""
    test = await db.ab_tests.find_one({"_id": ObjectId(test_id)})
    if not test:
        return None
    
    test["id"] = str(test.pop("_id"))
    
    # Calculate conversion rates
    metrics = test.get("metrics", {})
    for variant in ["variant_a", "variant_b"]:
        data = metrics.get(variant, {})
        impressions = data.get("impressions", 0)
        conversions = data.get("conversions", 0)
        data["conversion_rate"] = round((conversions / max(impressions, 1)) * 100, 2)
    
    # Determine winner
    rate_a = metrics.get("variant_a", {}).get("conversion_rate", 0)
    rate_b = metrics.get("variant_b", {}).get("conversion_rate", 0)
    
    if abs(rate_a - rate_b) < 1:  # Within 1% is inconclusive
        test["winner"] = "inconclusive"
    elif rate_a > rate_b:
        test["winner"] = "variant_a"
    else:
        test["winner"] = "variant_b"
    
    test["lift_percent"] = round(abs(rate_a - rate_b), 2)
    
    return test

async def get_active_ab_tests(db) -> List[Dict[str, Any]]:
    """Get all active A/B tests"""
    tests = await db.ab_tests.find({"status": "active"}).to_list(50)
    for t in tests:
        t["id"] = str(t.pop("_id"))
        t["created_at"] = t["created_at"].isoformat()
    return tests

async def end_ab_test(
    db,
    test_id: str,
    winner_id: str,
    ended_by: str
) -> bool:
    """End an A/B test and activate the winner"""
    test = await db.ab_tests.find_one({"_id": ObjectId(test_id)})
    if not test:
        return False
    
    # End the test
    await db.ab_tests.update_one(
        {"_id": ObjectId(test_id)},
        {"$set": {
            "status": "completed",
            "ended_at": datetime.now(timezone.utc),
            "ended_by": ended_by,
            "winner_id": winner_id
        }}
    )
    
    # Activate winner
    await activate_template_version(db, winner_id, ended_by)
    
    return True
