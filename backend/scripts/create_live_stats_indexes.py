"""
Database Migration Script: Create indexes for Live Stats & Admin Panel performance
Run this on production to fix slow/timing out admin panel endpoints
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def create_live_stats_indexes():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'creatorstudio_production')
    
    print(f"Connecting to {db_name}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("Creating indexes for admin panel performance...")
    
    indexes_to_create = [
        ("user_sessions", [("last_active", -1)]),
        ("user_activity_log", [("timestamp", -1)]),
        ("user_activity_log", [("user_id", 1), ("timestamp", -1)]),
        ("reel_generator_jobs", [("created_at", -1)]),
        ("reel_generator_jobs", [("user_id", 1), ("created_at", -1)]),
        ("story_generator_jobs", [("created_at", -1)]),
        ("story_generator_jobs", [("user_id", 1), ("created_at", -1)]),
        ("login_activity", [("timestamp", -1)]),
    ]
    
    for collection_name, index_keys in indexes_to_create:
        try:
            await db[collection_name].create_index(index_keys)
            print(f"✅ {collection_name}: {index_keys}")
        except Exception as e:
            print(f"⚠️ {collection_name}: {e}")
    
    print("\nDone! Admin panel should now be faster.")
    client.close()

if __name__ == "__main__":
    asyncio.run(create_live_stats_indexes())
