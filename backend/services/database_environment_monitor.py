"""
Database Environment Monitoring Service
Monitors database connections and sends alerts for environment mismatches
Includes automatic reconnection to production database
"""
import os
import asyncio
import subprocess
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

# Production configuration
PRODUCTION_DOMAIN = "www.visionary-suite.com"
PRODUCTION_API_URL = "https://www.visionary-suite.com"
ADMIN_PANEL_URL = "https://www.visionary-suite.com/app/admin/environment-monitor"

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
        self.auto_fix_enabled = True  # Enable automatic reconnection
    
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
            
            # Attempt automatic reconnection if enabled
            if self.auto_fix_enabled:
                fix_result = await self.attempt_auto_reconnect()
                result["auto_fix_attempted"] = True
                result["auto_fix_result"] = fix_result
        
        return result
    
    async def attempt_auto_reconnect(self) -> Dict[str, Any]:
        """
        Attempt to automatically reconnect to production database.
        This will update the .env file and restart the backend service.
        """
        try:
            logger.warning("Attempting automatic database reconnection to production...")
            
            # Log the attempt
            await self.db.environment_fix_attempts.insert_one({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "AUTO_RECONNECT_ATTEMPT",
                "current_db": self.db_name,
                "target_db": EXPECTED_PRODUCTION_DB,
                "status": "INITIATED"
            })
            
            # Read current .env file
            env_path = "/app/backend/.env"
            current_env = {}
            
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            current_env[key] = value.strip('"\'')
            except Exception as e:
                logger.error(f"Failed to read .env file: {e}")
                return {"success": False, "error": f"Failed to read .env: {e}"}
            
            # Check if DB_NAME needs updating
            current_db_name = current_env.get("DB_NAME", "")
            if current_db_name == EXPECTED_PRODUCTION_DB:
                logger.info("DB_NAME is already set to production database")
                return {
                    "success": True, 
                    "message": "Database already configured for production",
                    "db_name": EXPECTED_PRODUCTION_DB
                }
            
            # Update DB_NAME to production
            current_env["DB_NAME"] = EXPECTED_PRODUCTION_DB
            
            # Write updated .env file
            try:
                with open(env_path, 'w') as f:
                    for key, value in current_env.items():
                        # Handle values that need quotes
                        if ' ' in str(value) or '#' in str(value):
                            f.write(f'{key}="{value}"\n')
                        else:
                            f.write(f'{key}={value}\n')
                
                logger.info(f"Updated DB_NAME in .env to {EXPECTED_PRODUCTION_DB}")
            except Exception as e:
                logger.error(f"Failed to write .env file: {e}")
                return {"success": False, "error": f"Failed to write .env: {e}"}
            
            # Restart backend service
            try:
                restart_result = subprocess.run(
                    ["sudo", "supervisorctl", "restart", "backend"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if restart_result.returncode == 0:
                    logger.info("Backend service restart initiated successfully")
                    
                    # Update fix attempt record
                    await self.db.environment_fix_attempts.update_one(
                        {"status": "INITIATED"},
                        {"$set": {
                            "status": "SUCCESS",
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "new_db_name": EXPECTED_PRODUCTION_DB
                        }},
                        sort=[("timestamp", -1)]
                    )
                    
                    return {
                        "success": True,
                        "message": "Database reconnected to production and service restarted",
                        "new_db_name": EXPECTED_PRODUCTION_DB,
                        "service_restart": "SUCCESS"
                    }
                else:
                    logger.error(f"Backend restart failed: {restart_result.stderr}")
                    return {
                        "success": False,
                        "error": f"Service restart failed: {restart_result.stderr}"
                    }
                    
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Service restart timed out"}
            except Exception as e:
                return {"success": False, "error": f"Service restart error: {e}"}
                
        except Exception as e:
            logger.error(f"Auto reconnect failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def manual_reconnect_to_production(self) -> Dict[str, Any]:
        """
        Manually trigger reconnection to production database.
        Called from admin panel or email action button.
        """
        logger.info("Manual production database reconnection triggered")
        
        # Send notification about manual fix
        await self._send_fix_notification("MANUAL")
        
        # Perform the reconnection
        result = await self.attempt_auto_reconnect()
        
        # Log the result
        await self.db.environment_fix_attempts.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "MANUAL_RECONNECT",
            "triggered_by": "admin_panel",
            "result": result
        })
        
        return result
    
    async def _send_fix_notification(self, trigger_type: str):
        """Send notification that a fix is being attempted"""
        if not self.sg:
            return
        
        try:
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #10b981;">🔧 Database Reconnection Initiated</h2>
                <p>A database reconnection to production has been triggered.</p>
                <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>Trigger Type:</strong> {trigger_type}</p>
                    <p><strong>Target Database:</strong> {EXPECTED_PRODUCTION_DB}</p>
                    <p><strong>Timestamp:</strong> {datetime.now(timezone.utc).isoformat()}</p>
                </div>
                <p>The system will attempt to update the database connection and restart services.</p>
            </body>
            </html>
            """
            
            for recipient in ALERT_RECIPIENTS:
                message = Mail(
                    from_email=Email(SENDER_EMAIL, "Visionary Suite Alerts"),
                    to_emails=To(recipient),
                    subject="🔧 Database Reconnection Initiated - www.visionary-suite.com",
                    html_content=HtmlContent(html_content)
                )
                self.sg.send(message)
                
        except Exception as e:
            logger.error(f"Failed to send fix notification: {e}")
    
    async def _send_alert(self, mismatch_info: Dict[str, Any]) -> bool:
        """Send alert email for environment mismatch with action button"""
        
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
        
        # Generate HTML email with action button
        severity_color = {
            "CRITICAL": "#dc2626",
            "HIGH": "#f59e0b",
            "MEDIUM": "#3b82f6",
            "INFO": "#6b7280"
        }.get(mismatch_info["severity"], "#6b7280")
        
        # Create the fix action URL
        fix_action_url = f"{PRODUCTION_API_URL}/api/environment-monitor/reconnect-production"
        admin_panel_url = ADMIN_PANEL_URL
        
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
                .action-button {{ 
                    display: inline-block; 
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                    color: white !important; 
                    padding: 15px 30px; 
                    border-radius: 8px; 
                    text-decoration: none; 
                    font-weight: bold; 
                    font-size: 16px;
                    margin: 10px 5px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
                }}
                .action-button:hover {{ background: linear-gradient(135deg, #059669 0%, #047857 100%); }}
                .secondary-button {{
                    display: inline-block;
                    background: #4f46e5;
                    color: white !important;
                    padding: 12px 25px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 14px;
                    margin: 10px 5px;
                }}
                .action-section {{
                    background: #fef3c7;
                    border: 2px solid #f59e0b;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    text-align: center;
                }}
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
                    <p><span class="label">Expected Production DB:</span> <span class="value">{EXPECTED_PRODUCTION_DB}</span></p>
                    <p><span class="label">Is Localhost:</span> <span class="value">{mismatch_info['environment_info']['is_localhost']}</span></p>
                </div>
                
                <div class="action-section">
                    <h3 style="color: #92400e; margin-top: 0;">⚡ Quick Fix - Reconnect to Production Database</h3>
                    <p style="color: #78350f;">Click the button below to automatically reconnect www.visionary-suite.com to the Production database:</p>
                    
                    <a href="{admin_panel_url}" class="action-button" style="color: white;">
                        🔧 Open Admin Panel & Fix Now
                    </a>
                    
                    <p style="font-size: 12px; color: #78350f; margin-top: 15px;">
                        This will update the database configuration and restart the backend service.
                    </p>
                </div>
                
                <h3>⚠️ What This Means</h3>
                <div class="info-section" style="background: #fef2f2; border: 1px solid #dc2626;">
                    <p>The production website <strong>www.visionary-suite.com</strong> is currently connected to a <strong>non-production database</strong>.</p>
                    <p>This can cause:</p>
                    <ul>
                        <li>Data inconsistencies between environments</li>
                        <li>Missing production user data</li>
                        <li>Payment processing issues</li>
                        <li>User experience problems</li>
                    </ul>
                </div>
                
                <h3>Manual Fix Steps (If Auto-Fix Fails)</h3>
                <div class="info-section">
                    <ol>
                        <li>SSH into the production server</li>
                        <li>Edit <code>/app/backend/.env</code></li>
                        <li>Set <code>DB_NAME=creatorstudio_production</code></li>
                        <li>Run <code>sudo supervisorctl restart backend</code></li>
                        <li>Verify via the admin dashboard</li>
                    </ol>
                </div>
                
                <hr style="margin: 30px 0;">
                <p style="color: #6b7280; font-size: 12px;">
                    This is an automated alert from Visionary Suite Database Monitor.<br>
                    Auto-fix is {'ENABLED' if self.auto_fix_enabled else 'DISABLED'}.<br>
                    Alert sent to: {', '.join(ALERT_RECIPIENTS)}
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
                "alert_sent_to": ALERT_RECIPIENTS,
                "auto_fix_enabled": self.auto_fix_enabled
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
        
        # Get recent fix attempts
        recent_fixes = await self.db.environment_fix_attempts.find(
            {},
            {"_id": 0}
        ).sort("timestamp", -1).limit(5).to_list(5)
        
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
            "recent_fix_attempts": recent_fixes,
            "monitoring_active": True,
            "auto_fix_enabled": self.auto_fix_enabled,
            "alert_recipients": ALERT_RECIPIENTS,
            "last_check": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_fix_history(self, days: int = 30) -> list:
        """Get history of fix attempts"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        fixes = await self.db.environment_fix_attempts.find(
            {"timestamp": {"$gte": start_date.isoformat()}},
            {"_id": 0}
        ).sort("timestamp", -1).to_list(100)
        
        return fixes


# Singleton instance
_monitor = None

def get_environment_monitor(db, db_name: str, mongo_url: str):
    global _monitor
    if _monitor is None:
        _monitor = DatabaseEnvironmentMonitor(db, db_name, mongo_url)
    return _monitor
