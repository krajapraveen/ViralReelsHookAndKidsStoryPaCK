"""
Daily Visitor Report Service
Generates comprehensive daily reports and sends via email
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
import json
import logging

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "krajapraveen@visionary-suite.com")
REPORT_RECIPIENTS = ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"]


class DailyVisitorReportService:
    """Service to generate and send daily visitor reports"""
    
    def __init__(self, db):
        self.db = db
        self.sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY) if SENDGRID_API_KEY else None
    
    async def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive daily visitor report"""
        
        if date is None:
            date = datetime.now(timezone.utc)
        
        # Set date range for the report day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        start_iso = start_of_day.isoformat()
        end_iso = end_of_day.isoformat()
        
        report = {
            "report_date": date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "website": "www.visionary-suite.com",
            "sections": {}
        }
        
        # =====================================================
        # 1. VISITOR LIST (Old and New Users)
        # =====================================================
        
        # Get all users who logged in today
        login_sessions = await self.db.user_sessions.find({
            "loginTime": {"$gte": start_iso, "$lte": end_iso}
        }).to_list(1000)
        
        # Get all users created today (new users)
        new_users = await self.db.users.find({
            "createdAt": {"$gte": start_iso, "$lte": end_iso}
        }, {"_id": 0, "id": 1, "name": 1, "email": 1, "createdAt": 1, "plan": 1}).to_list(1000)
        
        # Get all users who were active today
        active_user_ids = list(set([s.get("userId") for s in login_sessions if s.get("userId")]))
        
        visitors = []
        for user_id in active_user_ids:
            user = await self.db.users.find_one(
                {"id": user_id}, 
                {"_id": 0, "id": 1, "name": 1, "email": 1, "createdAt": 1, "plan": 1, "credits": 1}
            )
            if user:
                # Check if new user
                is_new = any(nu.get("id") == user_id for nu in new_users)
                
                # Get user's sessions today
                user_sessions = [s for s in login_sessions if s.get("userId") == user_id]
                
                visitors.append({
                    "user_id": user_id,
                    "name": user.get("name", "Unknown"),
                    "email": user.get("email", ""),
                    "is_new_user": is_new,
                    "plan": user.get("plan", "free"),
                    "credits_remaining": user.get("credits", 0),
                    "login_count_today": len(user_sessions),
                    "first_login_today": min([s.get("loginTime", "") for s in user_sessions]) if user_sessions else None,
                    "last_activity_today": max([s.get("lastActivity", s.get("loginTime", "")) for s in user_sessions]) if user_sessions else None
                })
        
        report["sections"]["visitors"] = {
            "total_visitors_today": len(visitors),
            "new_users_today": len(new_users),
            "returning_users_today": len(visitors) - len([v for v in visitors if v["is_new_user"]]),
            "visitors_list": visitors
        }
        
        # =====================================================
        # 2. USER LOCATIONS (from IP geolocation if available)
        # =====================================================
        
        locations = await self.db.user_sessions.aggregate([
            {"$match": {"loginTime": {"$gte": start_iso, "$lte": end_iso}}},
            {"$group": {
                "_id": "$location",
                "count": {"$sum": 1},
                "users": {"$addToSet": "$userId"}
            }},
            {"$sort": {"count": -1}}
        ]).to_list(100)
        
        report["sections"]["locations"] = {
            "unique_locations": len(locations),
            "location_breakdown": [
                {"location": loc.get("_id", "Unknown"), "visitors": loc.get("count", 0), "unique_users": len(loc.get("users", []))}
                for loc in locations
            ]
        }
        
        # =====================================================
        # 3. ACTIVITIES PERFORMED
        # =====================================================
        
        # Get all generations/jobs today
        generations = await self.db.generations.find({
            "createdAt": {"$gte": start_iso, "$lte": end_iso}
        }, {"_id": 0}).to_list(1000)
        
        genstudio_jobs = await self.db.genstudio_jobs.find({
            "createdAt": {"$gte": start_iso, "$lte": end_iso}
        }, {"_id": 0}).to_list(1000)
        
        # Activity breakdown by type
        activity_by_type = {}
        for gen in generations:
            gen_type = gen.get("type", "unknown")
            if gen_type not in activity_by_type:
                activity_by_type[gen_type] = {"count": 0, "successful": 0, "failed": 0, "users": set()}
            activity_by_type[gen_type]["count"] += 1
            if gen.get("status") == "COMPLETED":
                activity_by_type[gen_type]["successful"] += 1
            elif gen.get("status") == "FAILED":
                activity_by_type[gen_type]["failed"] += 1
            if gen.get("userId"):
                activity_by_type[gen_type]["users"].add(gen.get("userId"))
        
        for job in genstudio_jobs:
            job_type = job.get("jobType", "unknown")
            if job_type not in activity_by_type:
                activity_by_type[job_type] = {"count": 0, "successful": 0, "failed": 0, "users": set()}
            activity_by_type[job_type]["count"] += 1
            if job.get("status") == "COMPLETED":
                activity_by_type[job_type]["successful"] += 1
            elif job.get("status") == "FAILED":
                activity_by_type[job_type]["failed"] += 1
            if job.get("userId"):
                activity_by_type[job_type]["users"].add(job.get("userId"))
        
        # Convert sets to counts
        for act_type in activity_by_type:
            activity_by_type[act_type]["unique_users"] = len(activity_by_type[act_type]["users"])
            del activity_by_type[act_type]["users"]
        
        report["sections"]["activities"] = {
            "total_activities": len(generations) + len(genstudio_jobs),
            "activity_breakdown": activity_by_type
        }
        
        # =====================================================
        # 4. FEATURES USED
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
        
        report["sections"]["features_used"] = [
            {
                "feature": f.get("_id", "Unknown"),
                "total_uses": f.get("total_uses", 0),
                "successful": f.get("successful", 0),
                "failed": f.get("failed", 0),
                "success_rate": round((f.get("successful", 0) / max(f.get("total_uses", 1), 1)) * 100, 1),
                "credits_consumed": f.get("credits_used", 0),
                "unique_users": len(f.get("unique_users", []))
            }
            for f in feature_usage
        ]
        
        # =====================================================
        # 5. FAILED FEATURE ACCESSES
        # =====================================================
        
        failed_jobs = await self.db.generations.find({
            "createdAt": {"$gte": start_iso, "$lte": end_iso},
            "status": "FAILED"
        }, {"_id": 0}).to_list(500)
        
        failed_genstudio = await self.db.genstudio_jobs.find({
            "createdAt": {"$gte": start_iso, "$lte": end_iso},
            "status": "FAILED"
        }, {"_id": 0}).to_list(500)
        
        all_failures = []
        for job in failed_jobs + failed_genstudio:
            user = await self.db.users.find_one({"id": job.get("userId")}, {"_id": 0, "name": 1, "email": 1})
            all_failures.append({
                "feature": job.get("type", job.get("jobType", "Unknown")),
                "user_name": user.get("name", "Unknown") if user else "Unknown",
                "user_email": user.get("email", "") if user else "",
                "timestamp": job.get("createdAt", ""),
                "error_message": job.get("error", job.get("errorMessage", "Unknown error")),
                "job_id": job.get("id", job.get("jobId", ""))
            })
        
        report["sections"]["failed_accesses"] = {
            "total_failures": len(all_failures),
            "failures_list": all_failures
        }
        
        # =====================================================
        # 6. RATE LIMITING EVENTS
        # =====================================================
        
        rate_limit_events = await self.db.rate_limit_logs.find({
            "timestamp": {"$gte": start_iso, "$lte": end_iso}
        }, {"_id": 0}).to_list(1000)
        
        rate_limit_by_ip = {}
        for event in rate_limit_events:
            ip = event.get("ip", "unknown")
            if ip not in rate_limit_by_ip:
                rate_limit_by_ip[ip] = {"count": 0, "endpoints": set(), "user_ids": set()}
            rate_limit_by_ip[ip]["count"] += 1
            rate_limit_by_ip[ip]["endpoints"].add(event.get("endpoint", ""))
            if event.get("userId"):
                rate_limit_by_ip[ip]["user_ids"].add(event.get("userId"))
        
        # Convert sets to lists
        for ip in rate_limit_by_ip:
            rate_limit_by_ip[ip]["endpoints"] = list(rate_limit_by_ip[ip]["endpoints"])
            rate_limit_by_ip[ip]["user_ids"] = list(rate_limit_by_ip[ip]["user_ids"])
        
        report["sections"]["rate_limiting"] = {
            "total_rate_limit_events": len(rate_limit_events),
            "unique_ips_rate_limited": len(rate_limit_by_ip),
            "rate_limit_by_ip": rate_limit_by_ip
        }
        
        # =====================================================
        # 7. SUSPICIOUS IPs
        # =====================================================
        
        # Criteria for suspicious IPs:
        # - Multiple failed login attempts
        # - High rate limiting count
        # - Multiple accounts from same IP
        # - Unusual activity patterns
        
        suspicious_ips = []
        
        # Get failed login attempts by IP
        failed_logins = await self.db.login_attempts.find({
            "timestamp": {"$gte": start_iso, "$lte": end_iso},
            "success": False
        }, {"_id": 0}).to_list(1000)
        
        failed_by_ip = {}
        for attempt in failed_logins:
            ip = attempt.get("ip", "unknown")
            if ip not in failed_by_ip:
                failed_by_ip[ip] = {"count": 0, "emails_tried": set()}
            failed_by_ip[ip]["count"] += 1
            failed_by_ip[ip]["emails_tried"].add(attempt.get("email", ""))
        
        for ip, data in failed_by_ip.items():
            reasons = []
            suspicion_score = 0
            
            if data["count"] >= 5:
                reasons.append(f"Multiple failed login attempts ({data['count']})")
                suspicion_score += 30
            
            if len(data["emails_tried"]) >= 3:
                reasons.append(f"Tried multiple different emails ({len(data['emails_tried'])})")
                suspicion_score += 40
            
            # Check rate limiting for this IP
            if ip in rate_limit_by_ip and rate_limit_by_ip[ip]["count"] >= 10:
                reasons.append(f"High rate limiting events ({rate_limit_by_ip[ip]['count']})")
                suspicion_score += 30
            
            if reasons:
                suspicious_ips.append({
                    "ip": ip,
                    "suspicion_score": suspicion_score,
                    "reasons": reasons,
                    "failed_login_attempts": data["count"],
                    "emails_tried": list(data["emails_tried"])
                })
        
        # Sort by suspicion score
        suspicious_ips.sort(key=lambda x: x["suspicion_score"], reverse=True)
        
        report["sections"]["suspicious_ips"] = {
            "total_suspicious_ips": len(suspicious_ips),
            "suspicious_ips_list": suspicious_ips
        }
        
        # =====================================================
        # 8. FREE CREDITS USAGE
        # =====================================================
        
        # Get credit transactions for today
        credit_transactions = await self.db.credit_transactions.find({
            "timestamp": {"$gte": start_iso, "$lte": end_iso},
            "type": "DEDUCT"
        }, {"_id": 0}).to_list(1000)
        
        free_credits_by_feature = {}
        free_credits_by_user = {}
        
        for txn in credit_transactions:
            feature = txn.get("feature", txn.get("reason", "Unknown"))
            user_id = txn.get("userId", "")
            credits = txn.get("amount", txn.get("credits", 0))
            
            # Feature breakdown
            if feature not in free_credits_by_feature:
                free_credits_by_feature[feature] = {"total_credits": 0, "transaction_count": 0, "users": set()}
            free_credits_by_feature[feature]["total_credits"] += abs(credits)
            free_credits_by_feature[feature]["transaction_count"] += 1
            free_credits_by_feature[feature]["users"].add(user_id)
            
            # User breakdown
            if user_id not in free_credits_by_user:
                free_credits_by_user[user_id] = {"total_credits": 0, "features_used": set()}
            free_credits_by_user[user_id]["total_credits"] += abs(credits)
            free_credits_by_user[user_id]["features_used"].add(feature)
        
        # Get user details
        free_credits_users_list = []
        for user_id, data in free_credits_by_user.items():
            user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "name": 1, "email": 1, "plan": 1})
            free_credits_users_list.append({
                "user_id": user_id,
                "name": user.get("name", "Unknown") if user else "Unknown",
                "email": user.get("email", "") if user else "",
                "plan": user.get("plan", "free") if user else "free",
                "total_credits_used": data["total_credits"],
                "features_used": list(data["features_used"])
            })
        
        # Convert sets for features
        for feature in free_credits_by_feature:
            free_credits_by_feature[feature]["unique_users"] = len(free_credits_by_feature[feature]["users"])
            del free_credits_by_feature[feature]["users"]
        
        report["sections"]["free_credits_usage"] = {
            "total_credits_used_today": sum(f["total_credits"] for f in free_credits_by_feature.values()),
            "by_feature": free_credits_by_feature,
            "by_user": free_credits_users_list
        }
        
        return report
    
    def format_html_report(self, report: Dict[str, Any]) -> str:
        """Format report as HTML email"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; }}
                h1 {{ color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }}
                h2 {{ color: #1f2937; margin-top: 30px; }}
                .section {{ background: #f9fafb; border-radius: 8px; padding: 20px; margin: 15px 0; }}
                .metric {{ display: inline-block; background: #eef2ff; padding: 15px 25px; border-radius: 8px; margin: 5px; text-align: center; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
                .metric-label {{ font-size: 12px; color: #6b7280; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
                th {{ background: #f3f4f6; font-weight: 600; }}
                .success {{ color: #10b981; }}
                .failure {{ color: #ef4444; }}
                .warning {{ color: #f59e0b; }}
                .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; }}
                .badge-new {{ background: #dcfce7; color: #16a34a; }}
                .badge-returning {{ background: #dbeafe; color: #2563eb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Daily Visitor Report - {report['report_date']}</h1>
                <p>Website: <strong>{report['website']}</strong></p>
                <p>Generated: {report['generated_at']}</p>
                
                <!-- Summary Metrics -->
                <div style="text-align: center; margin: 30px 0;">
                    <div class="metric">
                        <div class="metric-value">{report['sections']['visitors']['total_visitors_today']}</div>
                        <div class="metric-label">Total Visitors</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{report['sections']['visitors']['new_users_today']}</div>
                        <div class="metric-label">New Users</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{report['sections']['visitors']['returning_users_today']}</div>
                        <div class="metric-label">Returning Users</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{report['sections']['activities']['total_activities']}</div>
                        <div class="metric-label">Total Activities</div>
                    </div>
                </div>
        """
        
        # Visitors Section
        visitors = report['sections']['visitors']['visitors_list']
        if visitors:
            html += """
                <h2>Visitors Today</h2>
                <div class="section">
                    <table>
                        <tr>
                            <th>User</th>
                            <th>Email</th>
                            <th>Type</th>
                            <th>Plan</th>
                            <th>Logins</th>
                            <th>First Login</th>
                        </tr>
            """
            for v in visitors[:20]:  # Limit to 20
                user_type = '<span class="badge badge-new">NEW</span>' if v['is_new_user'] else '<span class="badge badge-returning">Returning</span>'
                first_login = v.get('first_login_today', '')[:19] if v.get('first_login_today') else 'N/A'
                html += f"""
                        <tr>
                            <td>{v['name']}</td>
                            <td>{v['email']}</td>
                            <td>{user_type}</td>
                            <td>{v['plan']}</td>
                            <td>{v['login_count_today']}</td>
                            <td>{first_login}</td>
                        </tr>
                """
            html += "</table></div>"
        
        # Features Used Section
        features = report['sections']['features_used']
        if features:
            html += """
                <h2>Features Used</h2>
                <div class="section">
                    <table>
                        <tr>
                            <th>Feature</th>
                            <th>Total Uses</th>
                            <th>Success Rate</th>
                            <th>Credits Used</th>
                            <th>Unique Users</th>
                        </tr>
            """
            for f in features:
                success_class = 'success' if f['success_rate'] >= 90 else 'warning' if f['success_rate'] >= 70 else 'failure'
                html += f"""
                        <tr>
                            <td><strong>{f['feature']}</strong></td>
                            <td>{f['total_uses']}</td>
                            <td class="{success_class}">{f['success_rate']}%</td>
                            <td>{f['credits_consumed']}</td>
                            <td>{f['unique_users']}</td>
                        </tr>
                """
            html += "</table></div>"
        
        # Failed Accesses Section
        failures = report['sections']['failed_accesses']
        if failures['total_failures'] > 0:
            html += f"""
                <h2>Failed Feature Accesses</h2>
                <div class="section">
                    <p class="failure"><strong>Total Failures: {failures['total_failures']}</strong></p>
                    <table>
                        <tr>
                            <th>Feature</th>
                            <th>User</th>
                            <th>Time</th>
                            <th>Error</th>
                        </tr>
            """
            for f in failures['failures_list'][:10]:
                html += f"""
                        <tr>
                            <td>{f['feature']}</td>
                            <td>{f['user_name']}</td>
                            <td>{f['timestamp'][:19] if f['timestamp'] else 'N/A'}</td>
                            <td class="failure">{f['error_message'][:50]}...</td>
                        </tr>
                """
            html += "</table></div>"
        
        # Rate Limiting Section
        rate_limit = report['sections']['rate_limiting']
        html += f"""
                <h2>Rate Limiting Events</h2>
                <div class="section">
                    <div class="metric">
                        <div class="metric-value">{rate_limit['total_rate_limit_events']}</div>
                        <div class="metric-label">Total Events</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{rate_limit['unique_ips_rate_limited']}</div>
                        <div class="metric-label">Unique IPs</div>
                    </div>
                </div>
        """
        
        # Suspicious IPs Section
        suspicious = report['sections']['suspicious_ips']
        if suspicious['total_suspicious_ips'] > 0:
            html += f"""
                <h2 style="color: #ef4444;">Suspicious IPs Detected</h2>
                <div class="section" style="background: #fef2f2;">
                    <p class="failure"><strong>Warning: {suspicious['total_suspicious_ips']} suspicious IP(s) detected</strong></p>
                    <table>
                        <tr>
                            <th>IP Address</th>
                            <th>Suspicion Score</th>
                            <th>Reasons</th>
                            <th>Failed Logins</th>
                        </tr>
            """
            for ip in suspicious['suspicious_ips_list']:
                html += f"""
                        <tr>
                            <td><strong>{ip['ip']}</strong></td>
                            <td class="failure">{ip['suspicion_score']}/100</td>
                            <td>{', '.join(ip['reasons'])}</td>
                            <td>{ip['failed_login_attempts']}</td>
                        </tr>
                """
            html += "</table></div>"
        
        # Free Credits Usage Section
        credits = report['sections']['free_credits_usage']
        html += f"""
                <h2>Free Credits Usage</h2>
                <div class="section">
                    <div class="metric">
                        <div class="metric-value">{credits['total_credits_used_today']}</div>
                        <div class="metric-label">Total Credits Used</div>
                    </div>
        """
        
        if credits['by_feature']:
            html += """
                    <h3>By Feature</h3>
                    <table>
                        <tr>
                            <th>Feature</th>
                            <th>Credits Used</th>
                            <th>Transactions</th>
                            <th>Users</th>
                        </tr>
            """
            for feature, data in credits['by_feature'].items():
                html += f"""
                        <tr>
                            <td>{feature}</td>
                            <td>{data['total_credits']}</td>
                            <td>{data['transaction_count']}</td>
                            <td>{data['unique_users']}</td>
                        </tr>
                """
            html += "</table>"
        
        html += """
                </div>
                
                <hr style="margin-top: 40px;">
                <p style="color: #6b7280; font-size: 12px; text-align: center;">
                    This is an automated daily report from Visionary Suite.<br>
                    Generated by the Daily Visitor Report Service.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_daily_report(self, report: Dict[str, Any] = None, recipients: List[str] = None) -> Dict[str, Any]:
        """Send the daily report via email"""
        
        if not self.sg:
            return {"success": False, "error": "SendGrid not configured"}
        
        if report is None:
            report = await self.generate_daily_report()
        
        if recipients is None:
            recipients = REPORT_RECIPIENTS
        
        html_content = self.format_html_report(report)
        
        results = []
        for recipient in recipients:
            try:
                message = Mail(
                    from_email=Email(SENDER_EMAIL, "Visionary Suite"),
                    to_emails=To(recipient),
                    subject=f"Daily Visitor Report - {report['report_date']} | Visionary Suite",
                    html_content=HtmlContent(html_content)
                )
                
                response = self.sg.send(message)
                results.append({
                    "recipient": recipient,
                    "success": response.status_code in [200, 201, 202],
                    "status_code": response.status_code
                })
                
                logger.info(f"Daily report sent to {recipient}: {response.status_code}")
                
            except Exception as e:
                logger.error(f"Failed to send daily report to {recipient}: {e}")
                results.append({
                    "recipient": recipient,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": all(r["success"] for r in results),
            "report_date": report['report_date'],
            "recipients": results
        }


# Singleton instance
_report_service = None

def get_report_service(db):
    global _report_service
    if _report_service is None:
        _report_service = DailyVisitorReportService(db)
    return _report_service
