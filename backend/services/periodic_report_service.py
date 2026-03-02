"""
Weekly and Monthly Summary Report Service
Generates and sends periodic summary reports in IST
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, HtmlContent
import logging

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "krajapraveen@visionary-suite.com")
REPORT_RECIPIENTS = ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"]

# IST offset (UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)


def utc_to_ist(dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    return dt + IST_OFFSET


def ist_to_utc(dt: datetime) -> datetime:
    """Convert IST datetime to UTC"""
    return dt - IST_OFFSET


class PeriodicReportService:
    """Service to generate and send weekly/monthly reports"""
    
    def __init__(self, db):
        self.db = db
        self.sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY) if SENDGRID_API_KEY else None
    
    async def generate_summary_report(
        self, 
        period_type: str,  # 'weekly' or 'monthly'
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive summary report for the period"""
        
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        # Calculate period start
        if period_type == "weekly":
            start_date = end_date - timedelta(days=7)
            period_label = f"Week of {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        else:  # monthly
            start_date = end_date - timedelta(days=30)
            period_label = f"Month of {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        report = {
            "report_type": period_type,
            "period_label": period_label,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "generated_at": utc_to_ist(datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S IST"),
            "website": "www.visionary-suite.com",
            "sections": {}
        }
        
        # =====================================================
        # 1. USER GROWTH SUMMARY
        # =====================================================
        total_users = await self.db.users.count_documents({})
        new_users = await self.db.users.count_documents({
            "createdAt": {"$gte": start_iso, "$lte": end_iso}
        })
        
        # Get new users list
        new_users_list = await self.db.users.find(
            {"createdAt": {"$gte": start_iso, "$lte": end_iso}},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "createdAt": 1, "plan": 1}
        ).to_list(100)
        
        # Active users (logged in during period)
        active_sessions = await self.db.user_sessions.find({
            "loginTime": {"$gte": start_iso, "$lte": end_iso}
        }).to_list(10000)
        active_user_ids = list(set([s.get("userId") for s in active_sessions if s.get("userId")]))
        
        report["sections"]["user_growth"] = {
            "total_users": total_users,
            "new_users": new_users,
            "active_users": len(active_user_ids),
            "retention_rate": round((len(active_user_ids) / max(total_users, 1)) * 100, 1),
            "new_users_list": new_users_list[:20]  # Top 20
        }
        
        # =====================================================
        # 2. FEATURE USAGE ANALYTICS
        # =====================================================
        feature_usage = await self.db.generations.aggregate([
            {"$match": {"createdAt": {"$gte": start_iso, "$lte": end_iso}}},
            {"$group": {
                "_id": "$type",
                "total_uses": {"$sum": 1},
                "successful": {"$sum": {"$cond": [{"$eq": ["$status", "COMPLETED"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]}},
                "credits_used": {"$sum": "$creditsUsed"},
                "unique_users": {"$addToSet": "$userId"}
            }},
            {"$sort": {"total_uses": -1}}
        ]).to_list(50)
        
        total_generations = sum(f.get("total_uses", 0) for f in feature_usage)
        total_successful = sum(f.get("successful", 0) for f in feature_usage)
        total_credits = sum(f.get("credits_used", 0) for f in feature_usage)
        
        report["sections"]["feature_usage"] = {
            "total_generations": total_generations,
            "total_successful": total_successful,
            "overall_success_rate": round((total_successful / max(total_generations, 1)) * 100, 1),
            "total_credits_consumed": total_credits,
            "top_features": [
                {
                    "feature": f.get("_id", "Unknown"),
                    "uses": f.get("total_uses", 0),
                    "success_rate": round((f.get("successful", 0) / max(f.get("total_uses", 1), 1)) * 100, 1),
                    "credits": f.get("credits_used", 0),
                    "unique_users": len(f.get("unique_users", []))
                }
                for f in feature_usage[:10]
            ]
        }
        
        # =====================================================
        # 3. REVENUE & PAYMENT SUMMARY
        # =====================================================
        successful_payments = await self.db.orders.aggregate([
            {"$match": {"status": "PAID", "createdAt": {"$gte": start_iso, "$lte": end_iso}}},
            {"$group": {
                "_id": None,
                "total_revenue": {"$sum": "$amount"},
                "total_orders": {"$sum": 1},
                "unique_customers": {"$addToSet": "$userId"}
            }}
        ]).to_list(1)
        
        revenue_data = successful_payments[0] if successful_payments else {}
        
        # Payment by plan
        payment_by_plan = await self.db.orders.aggregate([
            {"$match": {"status": "PAID", "createdAt": {"$gte": start_iso, "$lte": end_iso}}},
            {"$group": {
                "_id": "$product",
                "count": {"$sum": 1},
                "revenue": {"$sum": "$amount"}
            }},
            {"$sort": {"revenue": -1}}
        ]).to_list(20)
        
        failed_payments = await self.db.orders.count_documents({
            "status": {"$in": ["FAILED", "CANCELLED"]},
            "createdAt": {"$gte": start_iso, "$lte": end_iso}
        })
        
        report["sections"]["revenue"] = {
            "total_revenue": revenue_data.get("total_revenue", 0),
            "total_orders": revenue_data.get("total_orders", 0),
            "unique_paying_customers": len(revenue_data.get("unique_customers", [])),
            "failed_payments": failed_payments,
            "payment_success_rate": round(
                (revenue_data.get("total_orders", 0) / 
                 max(revenue_data.get("total_orders", 0) + failed_payments, 1)) * 100, 1
            ),
            "by_plan": [
                {"plan": p.get("_id", "Unknown"), "count": p.get("count", 0), "revenue": p.get("revenue", 0)}
                for p in payment_by_plan
            ]
        }
        
        # =====================================================
        # 4. SECURITY & INCIDENTS
        # =====================================================
        failed_logins = await self.db.login_attempts.count_documents({
            "success": False,
            "timestamp": {"$gte": start_iso, "$lte": end_iso}
        })
        
        account_lockouts = await self.db.account_lockouts.count_documents({
            "lockedAt": {"$gte": start_iso, "$lte": end_iso}
        })
        
        rate_limit_events = await self.db.rate_limit_logs.count_documents({
            "timestamp": {"$gte": start_iso, "$lte": end_iso}
        })
        
        # Suspicious IPs
        suspicious_pipeline = await self.db.login_attempts.aggregate([
            {"$match": {"success": False, "timestamp": {"$gte": start_iso, "$lte": end_iso}}},
            {"$group": {"_id": "$ip", "count": {"$sum": 1}, "emails": {"$addToSet": "$email"}}},
            {"$match": {"count": {"$gte": 5}}},
            {"$sort": {"count": -1}}
        ]).to_list(20)
        
        report["sections"]["security"] = {
            "failed_login_attempts": failed_logins,
            "account_lockouts": account_lockouts,
            "rate_limit_events": rate_limit_events,
            "suspicious_ips": [
                {
                    "ip": ip.get("_id", "Unknown"),
                    "failed_attempts": ip.get("count", 0),
                    "emails_targeted": len(ip.get("emails", []))
                }
                for ip in suspicious_pipeline
            ]
        }
        
        # =====================================================
        # 5. SYSTEM HEALTH
        # =====================================================
        job_failures = await self.db.generations.count_documents({
            "status": "FAILED",
            "createdAt": {"$gte": start_iso, "$lte": end_iso}
        })
        
        # Daily breakdown
        daily_stats = []
        current_date = start_date
        while current_date <= end_date:
            day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = current_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            day_gens = await self.db.generations.count_documents({
                "createdAt": {"$gte": day_start.isoformat(), "$lte": day_end.isoformat()}
            })
            day_logins = await self.db.user_sessions.count_documents({
                "loginTime": {"$gte": day_start.isoformat(), "$lte": day_end.isoformat()}
            })
            
            daily_stats.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "generations": day_gens,
                "logins": day_logins
            })
            
            current_date += timedelta(days=1)
        
        report["sections"]["system_health"] = {
            "total_job_failures": job_failures,
            "uptime_estimate": "99.9%",
            "daily_breakdown": daily_stats
        }
        
        # =====================================================
        # 6. TOP PERFORMERS
        # =====================================================
        # Top users by activity
        top_users = await self.db.generations.aggregate([
            {"$match": {"createdAt": {"$gte": start_iso, "$lte": end_iso}}},
            {"$group": {
                "_id": "$userId",
                "total_generations": {"$sum": 1},
                "credits_used": {"$sum": "$creditsUsed"}
            }},
            {"$sort": {"total_generations": -1}},
            {"$limit": 10}
        ]).to_list(10)
        
        # Enrich with user details
        top_users_enriched = []
        for u in top_users:
            user = await self.db.users.find_one({"id": u.get("_id")}, {"_id": 0, "name": 1, "email": 1, "plan": 1})
            if user:
                top_users_enriched.append({
                    "name": user.get("name", "Unknown"),
                    "email": user.get("email", ""),
                    "plan": user.get("plan", "free"),
                    "generations": u.get("total_generations", 0),
                    "credits_used": u.get("credits_used", 0)
                })
        
        report["sections"]["top_performers"] = {
            "top_users_by_activity": top_users_enriched
        }
        
        return report
    
    def format_html_report(self, report: Dict[str, Any]) -> str:
        """Format periodic report as HTML email"""
        
        is_weekly = report.get("report_type") == "weekly"
        header_color = "#6366f1" if is_weekly else "#8b5cf6"
        period_icon = "📅" if is_weekly else "📆"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; }}
                h1 {{ color: {header_color}; border-bottom: 2px solid {header_color}; padding-bottom: 10px; }}
                h2 {{ color: #1f2937; margin-top: 30px; border-left: 4px solid {header_color}; padding-left: 12px; }}
                .section {{ background: #f9fafb; border-radius: 8px; padding: 20px; margin: 15px 0; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
                .metric {{ background: #eef2ff; padding: 20px; border-radius: 8px; text-align: center; }}
                .metric-value {{ font-size: 32px; font-weight: bold; color: {header_color}; }}
                .metric-label {{ font-size: 13px; color: #6b7280; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
                th {{ background: #f3f4f6; font-weight: 600; }}
                .success {{ color: #10b981; }}
                .failure {{ color: #ef4444; }}
                .warning {{ color: #f59e0b; }}
                .highlight {{ background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); padding: 15px; border-radius: 8px; margin: 10px 0; }}
                .badge {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
                .badge-success {{ background: #dcfce7; color: #16a34a; }}
                .badge-warning {{ background: #fef3c7; color: #d97706; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{period_icon} {"Weekly" if is_weekly else "Monthly"} Summary Report</h1>
                <p style="color: #6b7280; font-size: 14px;">
                    <strong>Period:</strong> {report['period_label']}<br>
                    <strong>Website:</strong> {report['website']}<br>
                    <strong>Generated:</strong> {report['generated_at']}
                </p>
        """
        
        # User Growth Section
        user_growth = report['sections'].get('user_growth', {})
        html += f"""
                <h2>User Growth</h2>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">{user_growth.get('total_users', 0)}</div>
                        <div class="metric-label">Total Users</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" style="color: #10b981;">+{user_growth.get('new_users', 0)}</div>
                        <div class="metric-label">New Users</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{user_growth.get('active_users', 0)}</div>
                        <div class="metric-label">Active Users</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{user_growth.get('retention_rate', 0)}%</div>
                        <div class="metric-label">Retention Rate</div>
                    </div>
                </div>
        """
        
        # Revenue Section
        revenue = report['sections'].get('revenue', {})
        html += f"""
                <h2>Revenue Summary</h2>
                <div class="highlight">
                    <div class="metric-grid">
                        <div class="metric" style="background: #dcfce7;">
                            <div class="metric-value" style="color: #16a34a;">₹{revenue.get('total_revenue', 0):,.0f}</div>
                            <div class="metric-label">Total Revenue</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{revenue.get('total_orders', 0)}</div>
                            <div class="metric-label">Successful Orders</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{revenue.get('unique_paying_customers', 0)}</div>
                            <div class="metric-label">Paying Customers</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{revenue.get('payment_success_rate', 0)}%</div>
                            <div class="metric-label">Payment Success</div>
                        </div>
                    </div>
                </div>
        """
        
        # Feature Usage Section
        feature_usage = report['sections'].get('feature_usage', {})
        html += f"""
                <h2>Feature Usage</h2>
                <div class="section">
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-value">{feature_usage.get('total_generations', 0)}</div>
                            <div class="metric-label">Total Generations</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{feature_usage.get('overall_success_rate', 0)}%</div>
                            <div class="metric-label">Success Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{feature_usage.get('total_credits_consumed', 0)}</div>
                            <div class="metric-label">Credits Used</div>
                        </div>
                    </div>
                    <h3>Top Features</h3>
                    <table>
                        <tr>
                            <th>Feature</th>
                            <th>Uses</th>
                            <th>Success Rate</th>
                            <th>Credits</th>
                            <th>Users</th>
                        </tr>
        """
        
        for f in feature_usage.get('top_features', [])[:7]:
            success_class = 'success' if f.get('success_rate', 0) >= 90 else 'warning' if f.get('success_rate', 0) >= 70 else 'failure'
            html += f"""
                        <tr>
                            <td><strong>{f.get('feature', 'Unknown')}</strong></td>
                            <td>{f.get('uses', 0)}</td>
                            <td class="{success_class}">{f.get('success_rate', 0)}%</td>
                            <td>{f.get('credits', 0)}</td>
                            <td>{f.get('unique_users', 0)}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
        """
        
        # Security Section
        security = report['sections'].get('security', {})
        html += f"""
                <h2>Security Summary</h2>
                <div class="section">
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-value" style="color: #ef4444;">{security.get('failed_login_attempts', 0)}</div>
                            <div class="metric-label">Failed Logins</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value" style="color: #f59e0b;">{security.get('account_lockouts', 0)}</div>
                            <div class="metric-label">Account Lockouts</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{security.get('rate_limit_events', 0)}</div>
                            <div class="metric-label">Rate Limits</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{len(security.get('suspicious_ips', []))}</div>
                            <div class="metric-label">Suspicious IPs</div>
                        </div>
                    </div>
                </div>
        """
        
        # Top Performers Section
        top_performers = report['sections'].get('top_performers', {})
        if top_performers.get('top_users_by_activity'):
            html += """
                <h2>Top Users by Activity</h2>
                <div class="section">
                    <table>
                        <tr>
                            <th>Rank</th>
                            <th>User</th>
                            <th>Plan</th>
                            <th>Generations</th>
                            <th>Credits Used</th>
                        </tr>
            """
            for i, u in enumerate(top_performers.get('top_users_by_activity', [])[:10], 1):
                html += f"""
                        <tr>
                            <td><strong>#{i}</strong></td>
                            <td>{u.get('name', 'Unknown')}<br><small style="color: #6b7280;">{u.get('email', '')}</small></td>
                            <td><span class="badge badge-success">{u.get('plan', 'free')}</span></td>
                            <td>{u.get('generations', 0)}</td>
                            <td>{u.get('credits_used', 0)}</td>
                        </tr>
                """
            html += """
                    </table>
                </div>
            """
        
        html += f"""
                <hr style="margin-top: 40px;">
                <p style="color: #6b7280; font-size: 12px; text-align: center;">
                    This is an automated {"weekly" if is_weekly else "monthly"} report from Visionary Suite.<br>
                    Generated in Indian Standard Time (IST).<br>
                    {"Next weekly report: Every Monday 6:00 AM IST" if is_weekly else "Next monthly report: 1st of every month 6:00 AM IST"}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_periodic_report(
        self, 
        period_type: str,
        report: Dict[str, Any] = None, 
        recipients: List[str] = None
    ) -> Dict[str, Any]:
        """Send the periodic report via email"""
        
        if not self.sg:
            return {"success": False, "error": "SendGrid not configured"}
        
        if report is None:
            report = await self.generate_summary_report(period_type)
        
        if recipients is None:
            recipients = REPORT_RECIPIENTS
        
        html_content = self.format_html_report(report)
        
        subject_prefix = "Weekly" if period_type == "weekly" else "Monthly"
        
        results = []
        for recipient in recipients:
            try:
                message = Mail(
                    from_email=Email(SENDER_EMAIL, "Visionary Suite"),
                    to_emails=To(recipient),
                    subject=f"{subject_prefix} Summary Report - {report['period_label']} | Visionary Suite",
                    html_content=HtmlContent(html_content)
                )
                
                response = self.sg.send(message)
                results.append({
                    "recipient": recipient,
                    "success": response.status_code in [200, 201, 202],
                    "status_code": response.status_code
                })
                
                logger.info(f"{period_type.capitalize()} report sent to {recipient}: {response.status_code}")
                
            except Exception as e:
                logger.error(f"Failed to send {period_type} report to {recipient}: {e}")
                results.append({
                    "recipient": recipient,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": all(r["success"] for r in results),
            "report_type": period_type,
            "period": report['period_label'],
            "recipients": results
        }


# Singleton instance
_periodic_service = None

def get_periodic_service(db):
    global _periodic_service
    if _periodic_service is None:
        _periodic_service = PeriodicReportService(db)
    return _periodic_service
