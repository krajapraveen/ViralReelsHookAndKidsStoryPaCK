"""
Daily Report Scheduler
Runs background task to send daily reports at end of day
"""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import os

logger = logging.getLogger(__name__)

# Schedule time (23:55 UTC - end of day)
SCHEDULE_HOUR = 23
SCHEDULE_MINUTE = 55


class DailyReportScheduler:
    """Background scheduler for daily reports"""
    
    def __init__(self, db):
        self.db = db
        self.running = False
        self.task = None
    
    async def _send_daily_report(self):
        """Internal method to send the daily report"""
        try:
            from services.daily_report_service import get_report_service
            
            service = get_report_service(self.db)
            report = await service.generate_daily_report()
            result = await service.send_daily_report(report)
            
            # Log the scheduled send
            await self.db.audit_logs.insert_one({
                "action": "DAILY_REPORT_SENT",
                "admin_id": "SCHEDULER",
                "admin_email": "automated@visionary-suite.com",
                "report_date": report["report_date"],
                "recipients": result.get("recipients", []),
                "scheduled": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Scheduled daily report sent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled daily report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Daily report scheduler started")
        
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Calculate next run time
                next_run = now.replace(
                    hour=SCHEDULE_HOUR,
                    minute=SCHEDULE_MINUTE,
                    second=0,
                    microsecond=0
                )
                
                # If we've passed today's time, schedule for tomorrow
                if now >= next_run:
                    next_run += timedelta(days=1)
                
                # Wait until next run
                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Daily report scheduler: Next run at {next_run.isoformat()} (in {wait_seconds/3600:.1f} hours)")
                
                await asyncio.sleep(wait_seconds)
                
                # Check if still running after sleep
                if not self.running:
                    break
                
                # Send the daily report
                logger.info("Daily report scheduler: Sending scheduled report...")
                await self._send_daily_report()
                
                # Wait a bit before next iteration to avoid double-sending
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Daily report scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._scheduler_loop())
            logger.info("Daily report scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("Daily report scheduler stopped")


# Singleton instance
_scheduler = None

def get_scheduler(db):
    global _scheduler
    if _scheduler is None:
        _scheduler = DailyReportScheduler(db)
    return _scheduler


def start_scheduler(db):
    """Start the daily report scheduler"""
    scheduler = get_scheduler(db)
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the daily report scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
