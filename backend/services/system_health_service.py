"""
Production System Health Monitoring Service
Monitors: Database, API, Payment Gateway, Email Service
Sends automatic alerts when systems go down
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("system_health")

# Alert cooldown tracking (in-memory)
_last_alerts: Dict[str, datetime] = {}
ALERT_COOLDOWN_MINUTES = 15

# Health check results cache
_health_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 10


class SystemHealthService:
    def __init__(self, db):
        self.db = db
        self.sendgrid_api_key = os.environ.get("SENDGRID_API_KEY", "")
        self.cashfree_app_id = os.environ.get("CASHFREE_APP_ID", "")
        self.cashfree_secret = os.environ.get("CASHFREE_SECRET_KEY", "")
        self.alert_emails = ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"]
        
    async def check_database_health(self) -> Dict[str, Any]:
        """Check MongoDB connection and performance"""
        start_time = datetime.now(timezone.utc)
        try:
            # Test connection with a simple query
            result = await self.db.command("ping")
            
            # Test read performance
            read_start = datetime.now(timezone.utc)
            await self.db.users.find_one({})
            read_time = (datetime.now(timezone.utc) - read_start).total_seconds() * 1000
            
            # Get database stats
            stats = await self.db.command("dbStats")
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            status = "UP"
            if response_time > 1000:
                status = "DEGRADED"
            
            return {
                "service": "database",
                "status": status,
                "response_time_ms": round(response_time, 2),
                "read_time_ms": round(read_time, 2),
                "details": {
                    "collections": stats.get("collections", 0),
                    "data_size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
                    "index_size_mb": round(stats.get("indexSize", 0) / (1024 * 1024), 2),
                    "db_name": stats.get("db", "unknown")
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "service": "database",
                "status": "DOWN",
                "response_time_ms": None,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check API endpoint health"""
        start_time = datetime.now(timezone.utc)
        try:
            # Test internal endpoints
            endpoints_status = []
            
            # Check if critical collections are accessible
            critical_checks = [
                ("users", self.db.users.count_documents({})),
                ("orders", self.db.orders.count_documents({})),
                ("generations", self.db.generations.count_documents({})),
            ]
            
            for name, check in critical_checks:
                try:
                    check_start = datetime.now(timezone.utc)
                    count = await check
                    check_time = (datetime.now(timezone.utc) - check_start).total_seconds() * 1000
                    endpoints_status.append({
                        "endpoint": name,
                        "status": "UP",
                        "response_time_ms": round(check_time, 2),
                        "count": count
                    })
                except Exception as e:
                    endpoints_status.append({
                        "endpoint": name,
                        "status": "DOWN",
                        "error": str(e)
                    })
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Determine overall status
            down_count = sum(1 for e in endpoints_status if e["status"] == "DOWN")
            if down_count == 0:
                status = "UP"
            elif down_count < len(endpoints_status):
                status = "DEGRADED"
            else:
                status = "DOWN"
            
            return {
                "service": "api",
                "status": status,
                "response_time_ms": round(response_time, 2),
                "details": {
                    "endpoints_checked": len(endpoints_status),
                    "endpoints_up": len(endpoints_status) - down_count,
                    "endpoints": endpoints_status
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return {
                "service": "api",
                "status": "DOWN",
                "response_time_ms": None,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_payment_gateway_health(self) -> Dict[str, Any]:
        """Check Cashfree payment gateway connectivity"""
        start_time = datetime.now(timezone.utc)
        
        if not self.cashfree_app_id or not self.cashfree_secret:
            return {
                "service": "payment_gateway",
                "status": "NOT_CONFIGURED",
                "response_time_ms": None,
                "details": {"message": "Cashfree credentials not configured"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Test Cashfree API connectivity
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use the orders endpoint to check connectivity
                response = await client.get(
                    "https://api.cashfree.com/pg/orders",
                    headers={
                        "x-client-id": self.cashfree_app_id,
                        "x-client-secret": self.cashfree_secret,
                        "x-api-version": "2023-08-01"
                    },
                    params={"limit": 1}
                )
                
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                # 200, 401, 403 all indicate the API is reachable
                if response.status_code in [200, 401, 403]:
                    status = "UP"
                elif response.status_code >= 500:
                    status = "DOWN"
                else:
                    status = "UP"  # API is reachable
                
                return {
                    "service": "payment_gateway",
                    "status": status,
                    "response_time_ms": round(response_time, 2),
                    "details": {
                        "provider": "Cashfree",
                        "http_status": response.status_code,
                        "api_version": "2023-08-01"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except httpx.TimeoutException:
            return {
                "service": "payment_gateway",
                "status": "DOWN",
                "response_time_ms": None,
                "error": "Connection timeout",
                "details": {"provider": "Cashfree"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Payment gateway health check failed: {e}")
            return {
                "service": "payment_gateway",
                "status": "DOWN",
                "response_time_ms": None,
                "error": str(e),
                "details": {"provider": "Cashfree"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_email_service_health(self) -> Dict[str, Any]:
        """Check SendGrid email service connectivity"""
        start_time = datetime.now(timezone.utc)
        
        if not self.sendgrid_api_key:
            return {
                "service": "email_service",
                "status": "NOT_CONFIGURED",
                "response_time_ms": None,
                "details": {"message": "SendGrid API key not configured"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check SendGrid API status
                response = await client.get(
                    "https://api.sendgrid.com/v3/user/profile",
                    headers={
                        "Authorization": f"Bearer {self.sendgrid_api_key}"
                    }
                )
                
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    status = "UP"
                    profile = response.json()
                    details = {
                        "provider": "SendGrid",
                        "account": profile.get("email", "unknown"),
                        "http_status": response.status_code
                    }
                elif response.status_code == 401:
                    status = "AUTH_ERROR"
                    details = {"provider": "SendGrid", "error": "Invalid API key"}
                else:
                    status = "DEGRADED"
                    details = {"provider": "SendGrid", "http_status": response.status_code}
                
                return {
                    "service": "email_service",
                    "status": status,
                    "response_time_ms": round(response_time, 2),
                    "details": details,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except httpx.TimeoutException:
            return {
                "service": "email_service",
                "status": "DOWN",
                "response_time_ms": None,
                "error": "Connection timeout",
                "details": {"provider": "SendGrid"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Email service health check failed: {e}")
            return {
                "service": "email_service",
                "status": "DOWN",
                "response_time_ms": None,
                "error": str(e),
                "details": {"provider": "SendGrid"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_all_systems(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        global _health_cache, _cache_timestamp
        
        # Check cache
        if _cache_timestamp and (datetime.now(timezone.utc) - _cache_timestamp).total_seconds() < CACHE_TTL_SECONDS:
            return _health_cache
        
        # Run all checks in parallel
        results = await asyncio.gather(
            self.check_database_health(),
            self.check_api_health(),
            self.check_payment_gateway_health(),
            self.check_email_service_health(),
            return_exceptions=True
        )
        
        services = []
        for result in results:
            if isinstance(result, Exception):
                services.append({
                    "service": "unknown",
                    "status": "ERROR",
                    "error": str(result)
                })
            else:
                services.append(result)
        
        # Calculate overall health
        statuses = [s.get("status", "DOWN") for s in services]
        if all(s in ["UP", "NOT_CONFIGURED"] for s in statuses):
            overall_status = "HEALTHY"
        elif any(s == "DOWN" for s in statuses):
            overall_status = "CRITICAL"
        else:
            overall_status = "DEGRADED"
        
        health_report = {
            "overall_status": overall_status,
            "services": services,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "next_check_in_seconds": CACHE_TTL_SECONDS
        }
        
        # Update cache
        _health_cache = health_report
        _cache_timestamp = datetime.now(timezone.utc)
        
        # Check for alerts
        await self._check_and_send_alerts(services)
        
        return health_report
    
    async def _check_and_send_alerts(self, services: list):
        """Check if any service is down and send alert if needed"""
        global _last_alerts
        
        down_services = [s for s in services if s.get("status") == "DOWN"]
        
        if not down_services:
            return
        
        for service in down_services:
            service_name = service.get("service", "unknown")
            
            # Check cooldown
            last_alert = _last_alerts.get(service_name)
            if last_alert:
                time_since_alert = (datetime.now(timezone.utc) - last_alert).total_seconds() / 60
                if time_since_alert < ALERT_COOLDOWN_MINUTES:
                    logger.info(f"Alert for {service_name} in cooldown ({time_since_alert:.1f} min since last)")
                    continue
            
            # Send alert
            await self._send_health_alert(service)
            _last_alerts[service_name] = datetime.now(timezone.utc)
    
    async def _send_health_alert(self, service: dict):
        """Send email alert for down service"""
        if not self.sendgrid_api_key:
            logger.warning("Cannot send health alert - SendGrid not configured")
            return
        
        service_name = service.get("service", "unknown").replace("_", " ").title()
        error = service.get("error", "Unknown error")
        
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
            
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; font-size: 24px;">🚨 System Alert: {service_name} DOWN</h1>
                </div>
                <div style="background: #fff; border: 1px solid #e5e7eb; padding: 20px; border-radius: 0 0 10px 10px;">
                    <p style="color: #374151; font-size: 16px;">
                        A critical system is experiencing issues on <strong>visionary-suite.com</strong>
                    </p>
                    
                    <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0;">
                        <p style="margin: 0; color: #991b1b;"><strong>Service:</strong> {service_name}</p>
                        <p style="margin: 10px 0 0 0; color: #991b1b;"><strong>Status:</strong> DOWN</p>
                        <p style="margin: 10px 0 0 0; color: #991b1b;"><strong>Error:</strong> {error}</p>
                        <p style="margin: 10px 0 0 0; color: #991b1b;"><strong>Time:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    </div>
                    
                    <p style="color: #6b7280; font-size: 14px;">
                        This alert will not repeat for {ALERT_COOLDOWN_MINUTES} minutes.
                    </p>
                    
                    <a href="https://www.visionary-suite.com/app/admin/system-health" 
                       style="display: inline-block; background: #4f46e5; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; margin-top: 15px; font-weight: bold;">
                        Open Health Dashboard →
                    </a>
                </div>
            </div>
            """
            
            # Send to all alert recipients
            for alert_email in self.alert_emails:
                message = Mail(
                    from_email=Email("alerts@visionary-suite.com", "Visionary Suite Alerts"),
                    to_emails=To(alert_email),
                    subject=f"🚨 ALERT: {service_name} is DOWN - visionary-suite.com",
                    html_content=Content("text/html", html_content)
                )
                
                response = sg.send(message)
                logger.info(f"Health alert sent for {service_name} to {alert_email}: {response.status_code}")
            
            # Log to database
            await self.db.health_alerts.insert_one({
                "service": service.get("service"),
                "status": "DOWN",
                "error": error,
                "alert_sent_to": self.alert_emails,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
    
    async def get_alert_history(self, days: int = 7) -> list:
        """Get health alert history"""
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        alerts = await self.db.health_alerts.find(
            {"timestamp": {"$gte": start_date}},
            {"_id": 0}
        ).sort("timestamp", -1).limit(100).to_list(100)
        
        return alerts
    
    async def get_uptime_stats(self, days: int = 30) -> Dict[str, Any]:
        """Calculate uptime statistics for each service"""
        # This would require storing health check results
        # For now, return placeholder
        return {
            "period_days": days,
            "services": {
                "database": {"uptime_percent": 99.9, "incidents": 0},
                "api": {"uptime_percent": 99.9, "incidents": 0},
                "payment_gateway": {"uptime_percent": 99.9, "incidents": 0},
                "email_service": {"uptime_percent": 99.9, "incidents": 0}
            }
        }


# Singleton instance
_health_service: Optional[SystemHealthService] = None

def get_health_service(db) -> SystemHealthService:
    global _health_service
    if _health_service is None:
        _health_service = SystemHealthService(db)
    return _health_service
