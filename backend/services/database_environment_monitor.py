"""
Database Environment Monitoring Service
Monitors database connections and sends alerts for environment mismatches
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, HtmlContent
import logging
import hashlib

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "alerts@visionary-suite.com")
ALERT_RECIPIENTS = ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"]

# Expected database configuration for production
EXPECTED_PRODUCTION_DB = "creatorstudio_production"
EXPECTED_QA_DB = "creatorstudio_qa"
EXPECTED_PREVIEW_DB = "creatorstudio_preview"

# Environment markers
PRODUCTION_DOMAINS = ["www.visionary-suite.com", "visionary-suite.com"]
PREVIEW_DOMAINS = ["preview.emergentagent.com"]


class DatabaseEnvironmentMonitor:
    """Monitor database environment and alert on mismatches"""
    
    def __init__(self, db, db_name: str, mongo_url: str):
        self.db = db
        self.db_name = db_name
        self.mongo_url = mongo_url
        self.sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY) if SENDGRID_API_KEY else None
        self.last_alert_hash = None
        self.last_alert_time = None
        self.alert_cooldown_minutes = 15  # Don't send same alert within 15 minutes
    
    def detect_environment(self) -> Dict[str, Any]:
        """Detect current environment based on database and configuration"""
        
        # Analyze database name
        db_name_lower = self.db_name.lower()
        
        detected_env = "UNKNOWN"
        is_production_db = False
        is_qa_db = False
        is_preview_db = False
        
        if "production" in db_name_lower or "prod" in db_name_lower:
            detected_env = "PRODUCTION"
            is_production_db = True
        elif "qa" in db_name_lower or "test" in db_name_lower:
            detected_env = "QA"
            is_qa_db = True
        elif "preview" in db_name_lower or "staging" in db_name_lower or "dev" in db_name_lower:
            detected_env = "PREVIEW"
            is_preview_db = True
        
        # Check MongoDB URL for environment hints
        mongo_url_lower = self.mongo_url.lower()
        is_localhost = "localhost" in mongo_url_lower or "127.0.0.1" in mongo_url_lower
        is_cloud_db = "mongodb+srv" in mongo_url_lower or "mongodb.net" in mongo_url_lower
        
        return {
            "database_name": self.db_name,
            "detected_environment": detected_env,
            "is_production_db": is_production_db,
            "is_qa_db": is_qa_db,
            "is_preview_db": is_preview_db,
            "is_localhost": is_localhost,
            "is_cloud_db": is_cloud_db,
            "mongo_url_masked": self._mask_connection_string(self.mongo_url)
        }
    
    def _mask_connection_string(self, url: str) -> str:
        """Mask sensitive parts of connection string"""
        if "@" in url:
            parts = url.split("@")
            return f"***masked***@{parts[-1]}"
        return url[:20] + "..." if len(url) > 20 else url
    
    async def check_environment_mismatch(self, request_domain: str = None) -> Dict[str, Any]:
        """Check if there's an environment mismatch"""
        
        env_info = self.detect_environment()
        
        mismatch_detected = False
        mismatch_type = None
        severity = "INFO"
        
        # Determine if request is from production domain
        is_production_request = False
        if request_domain:
            is_production_request = any(prod_domain in request_domain.lower() for prod_domain in PRODUCTION_DOMAINS)
        
        # Check for mismatches
        if is_production_request:
            if env_info["is_qa_db"]:
                mismatch_detected = True
                mismatch_type = "PRODUCTION_USING_QA_DATABASE"
                severity = "CRITICAL"
            elif env_info["is_preview_db"]:
                mismatch_detected = True
                mismatch_type = "PRODUCTION_USING_PREVIEW_DATABASE"
                severity = "CRITICAL"
            elif env_info["is_localhost"]:
                mismatch_detected = True
                mismatch_type = "PRODUCTION_USING_LOCALHOST_DATABASE"
                severity = "HIGH"
        
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_domain": request_domain,
            "is_production_request": is_production_request,
            "environment_info": env_info,
            "mismatch_detected": mismatch_detected,
            "mismatch_type": mismatch_type,
            "severity": severity,
            "status": "ALERT" if mismatch_detected else "OK"
        }
        
        # Send alert if mismatch detected
        if mismatch_detected:
            await self._send_alert(result)
        
        return result
    
    async def _send_alert(self, mismatch_info: Dict[str, Any]) -> bool:
        """Send alert email for environment mismatch"""
        
        if not self.sg:
            logger.warning("SendGrid not configured - cannot send alert")
            return False
        
        # Create alert hash to prevent duplicate alerts
        alert_content = f"{mismatch_info['mismatch_type']}:{mismatch_info['environment_info']['database_name']}"
        alert_hash = hashlib.md5(alert_content.encode()).hexdigest()
        
        # Check cooldown
        now = datetime.now(timezone.utc)
        if (self.last_alert_hash == alert_hash and 
            self.last_alert_time and 
            (now - self.last_alert_time).total_seconds() < self.alert_cooldown_minutes * 60):
            logger.info(f"Alert cooldown active - skipping duplicate alert for {mismatch_info['mismatch_type']}")
            return False
        
        # Generate HTML email
        severity_color = {
            "CRITICAL": "#dc2626",
            "HIGH": "#f59e0b",
            "MEDIUM": "#3b82f6",
            "INFO": "#6b7280"
        }.get(mismatch_info["severity"], "#6b7280")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; border-top: 5px solid {severity_color}; }}
                .alert-header {{ color: {severity_color}; font-size: 24px; font-weight: bold; margin-bottom: 20px; }}
                .alert-badge {{ display: inline-block; background: {severity_color}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                .info-section {{ background: #f9fafb; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .label {{ font-weight: 600; color: #374151; }}
                .value {{ color: #1f2937; }}
                .critical {{ color: #dc2626; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="alert-header">
                    🚨 DATABASE ENVIRONMENT MISMATCH DETECTED
                </div>
                
                <p><span class="alert-badge">{mismatch_info['severity']}</span></p>
                
                <div class="info-section">
                    <p><span class="label">Website:</span> <span class="value">www.visionary-suite.com</span></p>
                    <p><span class="label">Mismatch Type:</span> <span class="value critical">{mismatch_info['mismatch_type']}</span></p>
                    <p><span class="label">Detected At:</span> <span class="value">{mismatch_info['timestamp']}</span></p>
                </div>
                
                <h3>Database Information</h3>
                <div class="info-section">
                    <p><span class="label">Current Database:</span> <span class="value">{mismatch_info['environment_info']['database_name']}</span></p>
                    <p><span class="label">Detected Environment:</span> <span class="value">{mismatch_info['environment_info']['detected_environment']}</span></p>
                    <p><span class="label">Connection:</span> <span class="value">{mismatch_info['environment_info']['mongo_url_masked']}</span></p>
                    <p><span class="label">Is Localhost:</span> <span class="value">{mismatch_info['environment_info']['is_localhost']}</span></p>
                </div>
                
                <h3>⚠️ Recommended Action</h3>
                <div class="info-section" style="background: #fef2f2; border: 1px solid #dc2626;">
                    <p>The production website is connected to a non-production database. This requires immediate attention.</p>
                    <p><strong>Steps to fix:</strong></p>
                    <ol>
                        <li>Check the production server's environment variables</li>
                        <li>Verify MONGO_URL and DB_NAME are set to production values</li>
                        <li>Restart the production backend service</li>
                        <li>Verify the fix by checking the admin dashboard</li>
                    </ol>
                </div>
                
                <hr style="margin: 30px 0;">
                <p style="color: #6b7280; font-size: 12px;">
                    This is an automated alert from Visionary Suite Database Monitor.<br>
                    Alert owned by: Admin User & Emergent Management
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            for recipient in ALERT_RECIPIENTS:
                message = Mail(
                    from_email=Email(SENDER_EMAIL, "Visionary Suite Alerts"),
                    to_emails=To(recipient),
                    subject=f"🚨 [{mismatch_info['severity']}] Database Environment Mismatch - www.visionary-suite.com",
                    html_content=HtmlContent(html_content)
                )
                
                response = self.sg.send(message)
                logger.info(f"Environment mismatch alert sent to {recipient}: {response.status_code}")
            
            # Update last alert info
            self.last_alert_hash = alert_hash
            self.last_alert_time = now
            
            # Log to database
            await self.db.environment_alerts.insert_one({
                "type": "DATABASE_ENVIRONMENT_MISMATCH",
                "mismatch_type": mismatch_info["mismatch_type"],
                "severity": mismatch_info["severity"],
                "database_name": mismatch_info["environment_info"]["database_name"],
                "detected_environment": mismatch_info["environment_info"]["detected_environment"],
                "timestamp": now.isoformat(),
                "alert_sent_to": ALERT_RECIPIENTS
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send environment mismatch alert: {e}")
            return False
    
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get comprehensive environment status"""
        
        env_info = self.detect_environment()
        
        # Get recent alerts
        recent_alerts = await self.db.environment_alerts.find(
            {},
            {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        # Determine overall health
        health = "HEALTHY"
        if env_info["is_qa_db"] or env_info["is_preview_db"]:
            health = "WARNING"
        
        return {
            "status": health,
            "current_environment": env_info,
            "expected_production_db": EXPECTED_PRODUCTION_DB,
            "is_correct_production_db": env_info["database_name"] == EXPECTED_PRODUCTION_DB,
            "recent_alerts": recent_alerts,
            "monitoring_active": True,
            "alert_recipients": ALERT_RECIPIENTS,
            "last_check": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
_monitor = None

def get_environment_monitor(db, db_name: str, mongo_url: str):
    global _monitor
    if _monitor is None:
        _monitor = DatabaseEnvironmentMonitor(db, db_name, mongo_url)
    return _monitor
