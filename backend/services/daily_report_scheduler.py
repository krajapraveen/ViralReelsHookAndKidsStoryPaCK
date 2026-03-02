"""
Daily Report Scheduler
Runs background task to send daily, weekly, and monthly reports
All times in Indian Standard Time (IST = UTC+5:30)
"""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import os

logger = logging.getLogger(__name__)

# IST offset
IST_OFFSET = timedelta(hours=5, minutes=30)

# Schedule times in IST (will be converted to UTC for scheduling)
# Daily: 11:59 PM IST = 6:29 PM UTC (previous day)
# Weekly: Monday 6:00 AM IST = Sunday 12:30 AM UTC
# Monthly: 1st of month 6:00 AM IST = Last day of prev month 12:30 AM UTC

DAILY_HOUR_IST = 23  # 11:59 PM IST
DAILY_MINUTE_IST = 59

WEEKLY_HOUR_IST = 6  # 6:00 AM IST (Monday)
WEEKLY_MINUTE_IST = 0

MONTHLY_HOUR_IST = 6  # 6:00 AM IST (1st of month)
MONTHLY_MINUTE_IST = 0


def ist_to_utc_time(hour: int, minute: int) -> tuple:
    """Convert IST time to UTC time"""
    # IST is UTC+5:30, so subtract 5 hours 30 minutes
    utc_hour = hour - 5
    utc_minute = minute - 30
    
    if utc_minute < 0:
        utc_minute += 60
        utc_hour -= 1
    
    if utc_hour < 0:
        utc_hour += 24
        # This means it's the previous day in UTC
    
    return utc_hour, utc_minute


class ComprehensiveReportScheduler:
    """Background scheduler for daily, weekly, and monthly reports"""
    
    def __init__(self, db):
        self.db = db
        self.running = False
        self.daily_task = None
        self.weekly_task = None
        self.monthly_task = None
    
    async def _send_daily_report(self):
        """Send daily report"""
        try:
            from services.daily_report_service import get_report_service
            
            service = get_report_service(self.db)
            report = await service.generate_daily_report()
            result = await service.send_daily_report(report)
            
            await self.db.audit_logs.insert_one({
                "action": "DAILY_REPORT_SENT",
                "admin_id": "SCHEDULER",
                "admin_email": "automated@visionary-suite.com",
                "report_date": report["report_date"],
                "recipients": result.get("recipients", []),
                "scheduled": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "timezone": "IST"
            })
            
            logger.info(f"Scheduled daily report sent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled daily report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_weekly_report(self):
        """Send weekly report"""
        try:
            from services.periodic_report_service import get_periodic_service
            
            service = get_periodic_service(self.db)
            report = await service.generate_summary_report("weekly")
            result = await service.send_periodic_report("weekly", report)
            
            await self.db.audit_logs.insert_one({
                "action": "WEEKLY_REPORT_SENT",
                "admin_id": "SCHEDULER",
                "admin_email": "automated@visionary-suite.com",
                "period": report["period_label"],
                "recipients": result.get("recipients", []),
                "scheduled": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "timezone": "IST"
            })
            
            logger.info(f"Scheduled weekly report sent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled weekly report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_monthly_report(self):
        """Send monthly report"""
        try:
            from services.periodic_report_service import get_periodic_service
            
            service = get_periodic_service(self.db)
            report = await service.generate_summary_report("monthly")
            result = await service.send_periodic_report("monthly", report)
            
            await self.db.audit_logs.insert_one({
                "action": "MONTHLY_REPORT_SENT",
                "admin_id": "SCHEDULER",
                "admin_email": "automated@visionary-suite.com",
                "period": report["period_label"],
                "recipients": result.get("recipients", []),
                "scheduled": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "timezone": "IST"
            })
            
            logger.info(f"Scheduled monthly report sent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled monthly report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _daily_scheduler_loop(self):
        """Daily report scheduler loop"""
        logger.info("Daily report scheduler started (11:59 PM IST)")
        
        utc_hour, utc_minute = ist_to_utc_time(DAILY_HOUR_IST, DAILY_MINUTE_IST)
        
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Calculate next run time
                next_run = now.replace(hour=utc_hour, minute=utc_minute, second=0, microsecond=0)
                
                if now >= next_run:
                    next_run += timedelta(days=1)
                
                wait_seconds = (next_run - now).total_seconds()
                ist_time = next_run + IST_OFFSET
                logger.info(f"Daily report: Next run at {ist_time.strftime('%Y-%m-%d %H:%M:%S')} IST (in {wait_seconds/3600:.1f} hours)")
                
                await asyncio.sleep(wait_seconds)
                
                if not self.running:
                    break
                
                logger.info("Sending scheduled daily report...")
                await self._send_daily_report()
                
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily scheduler loop: {e}")
                await asyncio.sleep(300)
    
    async def _weekly_scheduler_loop(self):
        """Weekly report scheduler loop - Every Monday 6:00 AM IST"""
        logger.info("Weekly report scheduler started (Monday 6:00 AM IST)")
        
        utc_hour, utc_minute = ist_to_utc_time(WEEKLY_HOUR_IST, WEEKLY_MINUTE_IST)
        
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Find next Monday
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and now.hour >= utc_hour:
                    days_until_monday = 7
                
                next_run = (now + timedelta(days=days_until_monday)).replace(
                    hour=utc_hour, minute=utc_minute, second=0, microsecond=0
                )
                
                wait_seconds = (next_run - now).total_seconds()
                ist_time = next_run + IST_OFFSET
                logger.info(f"Weekly report: Next run at {ist_time.strftime('%Y-%m-%d %H:%M:%S')} IST (in {wait_seconds/3600/24:.1f} days)")
                
                await asyncio.sleep(wait_seconds)
                
                if not self.running:
                    break
                
                logger.info("Sending scheduled weekly report...")
                await self._send_weekly_report()
                
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in weekly scheduler loop: {e}")
                await asyncio.sleep(300)
    
    async def _monthly_scheduler_loop(self):
        """Monthly report scheduler loop - 1st of month 6:00 AM IST"""
        logger.info("Monthly report scheduler started (1st of month 6:00 AM IST)")
        
        utc_hour, utc_minute = ist_to_utc_time(MONTHLY_HOUR_IST, MONTHLY_MINUTE_IST)
        
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Find 1st of next month
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                
                next_run = next_month.replace(hour=utc_hour, minute=utc_minute, second=0, microsecond=0)
                
                # If we're on the 1st and haven't run yet
                if now.day == 1 and now.hour < utc_hour:
                    next_run = now.replace(hour=utc_hour, minute=utc_minute, second=0, microsecond=0)
                
                wait_seconds = (next_run - now).total_seconds()
                ist_time = next_run + IST_OFFSET
                logger.info(f"Monthly report: Next run at {ist_time.strftime('%Y-%m-%d %H:%M:%S')} IST (in {wait_seconds/3600/24:.1f} days)")
                
                await asyncio.sleep(wait_seconds)
                
                if not self.running:
                    break
                
                logger.info("Sending scheduled monthly report...")
                await self._send_monthly_report()
                
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monthly scheduler loop: {e}")
                await asyncio.sleep(300)
    
    def start(self):
        """Start all schedulers"""
        if not self.running:
            self.running = True
            self.daily_task = asyncio.create_task(self._daily_scheduler_loop())
            self.weekly_task = asyncio.create_task(self._weekly_scheduler_loop())
            self.monthly_task = asyncio.create_task(self._monthly_scheduler_loop())
            logger.info("All report schedulers started (Daily, Weekly, Monthly)")
    
    def stop(self):
        """Stop all schedulers"""
        self.running = False
        for task in [self.daily_task, self.weekly_task, self.monthly_task]:
            if task:
                task.cancel()
        logger.info("All report schedulers stopped")


# Singleton instance
_scheduler = None

def get_scheduler(db):
    global _scheduler
    if _scheduler is None:
        _scheduler = ComprehensiveReportScheduler(db)
    return _scheduler


def start_scheduler(db):
    """Start the comprehensive report scheduler"""
    scheduler = get_scheduler(db)
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the comprehensive report scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
