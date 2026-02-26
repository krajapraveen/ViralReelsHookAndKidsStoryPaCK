"""
Database Index Management - Critical Indexes for Performance
Ensures all necessary indexes exist for optimal query performance
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Index definitions for each collection
INDEX_DEFINITIONS = {
    # User collection indexes
    "users": [
        {"keys": [("id", 1)], "options": {"unique": True, "name": "idx_user_id"}},
        {"keys": [("email", 1)], "options": {"unique": True, "name": "idx_user_email"}},
        {"keys": [("createdAt", -1)], "options": {"name": "idx_user_created"}},
        {"keys": [("role", 1)], "options": {"name": "idx_user_role"}},
    ],
    
    # Jobs collection indexes (critical for worker performance)
    "genstudio_jobs": [
        {"keys": [("id", 1)], "options": {"unique": True, "name": "idx_job_id"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_job_user"}},
        {"keys": [("status", 1)], "options": {"name": "idx_job_status"}},
        {"keys": [("jobType", 1)], "options": {"name": "idx_job_type"}},
        {"keys": [("createdAt", -1)], "options": {"name": "idx_job_created"}},
        # Compound index for worker query (most critical)
        {"keys": [("status", 1), ("jobType", 1), ("priority", 1), ("createdAt", 1)], 
         "options": {"name": "idx_job_worker_query"}},
        # Index for user's job history
        {"keys": [("userId", 1), ("createdAt", -1)], 
         "options": {"name": "idx_job_user_history"}},
        # Index for locked jobs
        {"keys": [("status", 1), ("lockedUntil", 1)], 
         "options": {"name": "idx_job_lock"}},
    ],
    
    # Generations collection
    "generations": [
        {"keys": [("id", 1)], "options": {"unique": True, "name": "idx_gen_id"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_gen_user"}},
        {"keys": [("userId", 1), ("createdAt", -1)], 
         "options": {"name": "idx_gen_user_history"}},
        {"keys": [("type", 1), ("createdAt", -1)], 
         "options": {"name": "idx_gen_type_created"}},
    ],
    
    # Credit ledger indexes
    "credit_ledger": [
        {"keys": [("userId", 1)], "options": {"name": "idx_ledger_user"}},
        {"keys": [("userId", 1), ("createdAt", -1)], 
         "options": {"name": "idx_ledger_user_history"}},
        {"keys": [("entryType", 1), ("status", 1)], 
         "options": {"name": "idx_ledger_type_status"}},
        {"keys": [("userId", 1), ("entryType", 1), ("status", 1)], 
         "options": {"name": "idx_ledger_user_holds"}},
        {"keys": [("refId", 1)], "options": {"name": "idx_ledger_ref"}},
    ],
    
    # Orders collection
    "orders": [
        {"keys": [("order_id", 1)], "options": {"unique": True, "name": "idx_order_id"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_order_user"}},
        {"keys": [("userId", 1), ("createdAt", -1)], 
         "options": {"name": "idx_order_user_history"}},
        {"keys": [("status", 1)], "options": {"name": "idx_order_status"}},
        {"keys": [("gateway", 1), ("status", 1)], 
         "options": {"name": "idx_order_gateway_status"}},
    ],
    
    # Analytics/visitor tracking
    "visitor_events": [
        {"keys": [("userId", 1)], "options": {"name": "idx_visitor_user"}},
        {"keys": [("sessionId", 1)], "options": {"name": "idx_visitor_session"}},
        {"keys": [("createdAt", -1)], "options": {"name": "idx_visitor_created"}},
        {"keys": [("event", 1), ("createdAt", -1)], 
         "options": {"name": "idx_visitor_event_created"}},
    ],
    
    # Sessions tracking
    "sessions": [
        {"keys": [("sessionId", 1)], "options": {"unique": True, "name": "idx_session_id"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_session_user"}},
        {"keys": [("loginAt", -1)], "options": {"name": "idx_session_login"}},
    ],
    
    # Feature events for analytics
    "feature_events": [
        {"keys": [("eventId", 1)], "options": {"unique": True, "name": "idx_feature_event_id"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_feature_user"}},
        {"keys": [("sessionId", 1)], "options": {"name": "idx_feature_session"}},
        {"keys": [("featureKey", 1), ("createdAt", -1)], 
         "options": {"name": "idx_feature_key_created"}},
        {"keys": [("createdAt", -1)], "options": {"name": "idx_feature_created"}},
    ],
    
    # User ratings
    "ratings": [
        {"keys": [("ratingId", 1)], "options": {"unique": True, "name": "idx_rating_id"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_rating_user"}},
        {"keys": [("featureKey", 1)], "options": {"name": "idx_rating_feature"}},
        {"keys": [("rating", 1)], "options": {"name": "idx_rating_score"}},
        {"keys": [("createdAt", -1)], "options": {"name": "idx_rating_created"}},
    ],
    
    # Idempotency keys
    "idempotency_keys": [
        {"keys": [("key", 1)], "options": {"unique": True, "name": "idx_idempotency_key"}},
        {"keys": [("expiresAt", 1)], "options": {"name": "idx_idempotency_expires", "expireAfterSeconds": 0}},
    ],
    
    # Fallback outputs
    "fallback_outputs": [
        {"keys": [("jobId", 1)], "options": {"unique": True, "name": "idx_fallback_job"}},
        {"keys": [("userId", 1)], "options": {"name": "idx_fallback_user"}},
        {"keys": [("createdAt", -1)], "options": {"name": "idx_fallback_created"}},
    ],
    
    # Dead letter queue
    "dead_letter_jobs": [
        {"keys": [("originalId", 1)], "options": {"name": "idx_dlq_original"}},
        {"keys": [("movedAt", -1)], "options": {"name": "idx_dlq_moved"}},
        {"keys": [("jobType", 1)], "options": {"name": "idx_dlq_type"}},
    ],
    
    # Alerts and incidents (self-healing)
    "alerts": [
        {"keys": [("created_at", -1)], "options": {"name": "idx_alert_created"}},
        {"keys": [("severity", 1)], "options": {"name": "idx_alert_severity"}},
        {"keys": [("resolved", 1)], "options": {"name": "idx_alert_resolved"}},
    ],
    
    "incidents": [
        {"keys": [("created_at", -1)], "options": {"name": "idx_incident_created"}},
        {"keys": [("correlation_id", 1)], "options": {"name": "idx_incident_correlation"}},
        {"keys": [("status", 1)], "options": {"name": "idx_incident_status"}},
    ],
}


async def create_all_indexes(db) -> Dict[str, Any]:
    """
    Create all indexes defined in INDEX_DEFINITIONS.
    Returns a report of created/existing indexes.
    """
    report = {
        "created": [],
        "existing": [],
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    for collection_name, indexes in INDEX_DEFINITIONS.items():
        collection = db[collection_name]
        
        for index_def in indexes:
            keys = index_def["keys"]
            options = index_def.get("options", {})
            index_name = options.get("name", f"idx_{collection_name}_auto")
            
            try:
                # Check if index already exists
                existing_indexes = await collection.index_information()
                
                if index_name in existing_indexes:
                    report["existing"].append({
                        "collection": collection_name,
                        "index": index_name
                    })
                    continue
                
                # Create the index
                await collection.create_index(keys, **options)
                report["created"].append({
                    "collection": collection_name,
                    "index": index_name,
                    "keys": [k[0] for k in keys]
                })
                logger.info(f"Created index {index_name} on {collection_name}")
                
            except Exception as e:
                error_msg = str(e)
                # Ignore "index already exists" errors
                if "already exists" not in error_msg.lower():
                    report["errors"].append({
                        "collection": collection_name,
                        "index": index_name,
                        "error": error_msg
                    })
                    logger.error(f"Failed to create index {index_name} on {collection_name}: {error_msg}")
                else:
                    report["existing"].append({
                        "collection": collection_name,
                        "index": index_name
                    })
    
    logger.info(f"Index creation complete: {len(report['created'])} created, {len(report['existing'])} existing, {len(report['errors'])} errors")
    return report


async def get_index_status(db) -> Dict[str, Any]:
    """Get the status of all indexes across collections"""
    status = {}
    
    for collection_name in INDEX_DEFINITIONS.keys():
        try:
            collection = db[collection_name]
            indexes = await collection.index_information()
            status[collection_name] = {
                "count": len(indexes),
                "indexes": list(indexes.keys())
            }
        except Exception as e:
            status[collection_name] = {"error": str(e)}
    
    return status


async def drop_unused_indexes(db, dry_run: bool = True) -> List[Dict[str, Any]]:
    """
    Find and optionally drop indexes not in INDEX_DEFINITIONS.
    Returns list of indexes to drop (or dropped).
    """
    to_drop = []
    
    # Build set of expected index names
    expected_indexes = set()
    for indexes in INDEX_DEFINITIONS.values():
        for index_def in indexes:
            if "name" in index_def.get("options", {}):
                expected_indexes.add(index_def["options"]["name"])
    
    for collection_name in INDEX_DEFINITIONS.keys():
        try:
            collection = db[collection_name]
            existing = await collection.index_information()
            
            for index_name in existing.keys():
                # Skip default _id index
                if index_name == "_id_":
                    continue
                
                if index_name not in expected_indexes:
                    to_drop.append({
                        "collection": collection_name,
                        "index": index_name
                    })
                    
                    if not dry_run:
                        await collection.drop_index(index_name)
                        logger.info(f"Dropped unused index {index_name} from {collection_name}")
        
        except Exception as e:
            logger.error(f"Error checking indexes for {collection_name}: {e}")
    
    return to_drop


async def analyze_slow_queries(db, threshold_ms: int = 100) -> List[Dict[str, Any]]:
    """
    Analyze slow queries and suggest indexes.
    Note: Requires profiling to be enabled on the database.
    """
    suggestions = []
    
    try:
        # Get recent slow queries from system.profile
        profile_data = await db.system.profile.find({
            "millis": {"$gt": threshold_ms}
        }).sort("ts", -1).limit(20).to_list(20)
        
        for query in profile_data:
            suggestions.append({
                "collection": query.get("ns", "").split(".")[-1],
                "query": str(query.get("query", {}))[:200],
                "duration_ms": query.get("millis"),
                "timestamp": str(query.get("ts")),
                "suggestion": "Consider adding index for frequently queried fields"
            })
    
    except Exception as e:
        logger.warning(f"Could not analyze slow queries (profiling may be disabled): {e}")
    
    return suggestions
