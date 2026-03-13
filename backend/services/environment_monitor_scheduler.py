"""
Environment Monitor Scheduler
Background task that periodically checks database environment
and sends alerts for mismatches
"""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import os
import aiohttp

logger = logging.getLogger(__name__)

# Check interval in minutes
CHECK_INTERVAL_MINUTES = 5

# Production URL to check
PRODUCTION_URL = "https://www.visionary-suite.com"
PREVIEW_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://remix-monetize-1.preview.emergentagent.com")


class EnvironmentMonitorScheduler:
    """Background scheduler for environment monitoring"""
    
    def __init__(self, db, db_name: str, mongo_url: str):
        self.db = db
        self.db_name = db_name
        self.mongo_url = mongo_url
        self.running = False
        self.task = None
    
    async def _check_and_alert(self):
        """Perform environment check and send alerts if needed"""
        try:
            from services.database_environment_monitor import get_environment_monitor
            
            monitor = get_environment_monitor(self.db, self.db_name, self.mongo_url)
            
            # Check for production environment mismatch
            result = await monitor.check_environment_mismatch("www.visionary-suite.com")
            
            if result.get("mismatch_detected"):
                logger.warning(f"Environment mismatch detected: {result.get('mismatch_type')}")
                
                # Log to database for audit
                await self.db.environment_checks.insert_one({
                    "check_time": datetime.now(timezone.utc).isoformat(),
                    "result": "MISMATCH",
                    "mismatch_type": result.get("mismatch_type"),
                    "database_name": self.db_name,
                    "alert_sent": True
                })
            else:
                logger.debug("Environment check passed - no mismatch")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in environment check: {e}")
            return {"error": str(e)}
    
    async def _verify_production_backend(self):
        """Verify production backend is responding and check its database"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check production health endpoint
                async with session.get(
                    f"{PRODUCTION_URL}/api/environment-monitor/health-check",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if production is using correct database
                        if not data.get("is_production"):
                            logger.warning(f"Production site using non-production database: {data.get('database')}")
                            
                            # Trigger alert
                            from services.database_environment_monitor import get_environment_monitor
                            monitor = get_environment_monitor(self.db, self.db_name, self.mongo_url)
                            
                            await monitor._send_alert({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "request_domain": "www.visionary-suite.com",
                                "is_production_request": True,
                                "environment_info": {
                                    "database_name": data.get("database", "Unknown"),
                                    "detected_environment": data.get("environment", "Unknown"),
                                    "is_production_db": data.get("is_production", False),
                                    "is_qa_db": "qa" in data.get("database", "").lower(),
                                    "is_preview_db": "preview" in data.get("database", "").lower(),
                                    "is_localhost": False,
                                    "is_cloud_db": True,
                                    "mongo_url_masked": "***"
                                },
                                "mismatch_detected": True,
                                "mismatch_type": f"PRODUCTION_USING_{data.get('environment', 'UNKNOWN').upper()}_DATABASE",
                                "severity": "CRITICAL"
                            })
                        
                        return data
                    else:
                        logger.warning(f"Production health check failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.debug(f"Could not reach production backend: {e}")
            return None
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info(f"Environment monitor scheduler started (checking every {CHECK_INTERVAL_MINUTES} minutes)")
        
        while self.running:
            try:
                # Perform local environment check
                await self._check_and_alert()
                
                # Try to verify production backend (if accessible)
                await self._verify_production_backend()
                
                # Wait for next check
                await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
                
            except asyncio.CancelledError:
                logger.info("Environment monitor scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in environment monitor loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._scheduler_loop())
            logger.info("Environment monitor scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("Environment monitor scheduler stopped")


# Singleton instance
_env_scheduler = None

def get_env_scheduler(db, db_name: str, mongo_url: str):
    global _env_scheduler
    if _env_scheduler is None:
        _env_scheduler = EnvironmentMonitorScheduler(db, db_name, mongo_url)
    return _env_scheduler


def start_env_scheduler(db, db_name: str, mongo_url: str):
    """Start the environment monitor scheduler"""
    scheduler = get_env_scheduler(db, db_name, mongo_url)
    scheduler.start()
    return scheduler


def stop_env_scheduler():
    """Stop the environment monitor scheduler"""
    global _env_scheduler
    if _env_scheduler:
        _env_scheduler.stop()
