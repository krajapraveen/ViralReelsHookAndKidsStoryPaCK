"""
Advanced Analytics Export Service
==================================
Enhanced export capabilities with multiple formats,
filtering, scheduling, and compression support.
"""
import os
import io
import csv
import json
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("analytics_export")


class ExportFormat:
    JSON = "json"
    CSV = "csv"
    EXCEL = "xlsx"
    PDF = "pdf"


class AnalyticsExportService:
    """
    Advanced analytics export with multiple formats and filtering
    """
    
    SUPPORTED_FORMATS = [ExportFormat.JSON, ExportFormat.CSV]
    
    def __init__(self, db):
        self.db = db
    
    async def export_template_analytics(
        self,
        template_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = ExportFormat.JSON,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Export template analytics data
        
        Args:
            template_type: Filter by template type
            start_date: Start of date range
            end_date: End of date range
            format: Export format (json, csv)
            include_details: Include detailed breakdown
            
        Returns:
            Export data with metadata
        """
        query = {}
        
        if template_type:
            query["template_type"] = template_type
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date.isoformat()
            if end_date:
                query["timestamp"]["$lte"] = end_date.isoformat()
        
        # Fetch analytics data
        analytics = await self.db.template_analytics.find(
            query, {"_id": 0}
        ).sort("timestamp", -1).to_list(10000)
        
        # Calculate summary
        summary = self._calculate_summary(analytics)
        
        # Format data
        if format == ExportFormat.CSV:
            export_data = self._to_csv(analytics)
            content_type = "text/csv"
            filename = f"template_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            export_data = {
                "export_info": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "format": format,
                    "record_count": len(analytics),
                    "filters": {
                        "template_type": template_type,
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None
                    }
                },
                "summary": summary,
                "data": analytics if include_details else analytics[:100]
            }
            content_type = "application/json"
            filename = f"template_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return {
            "data": export_data,
            "content_type": content_type,
            "filename": filename,
            "record_count": len(analytics)
        }
    
    async def export_user_activity(
        self,
        user_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = ExportFormat.JSON
    ) -> Dict[str, Any]:
        """Export user activity data"""
        query = {}
        
        if user_id:
            query["userId"] = user_id
        if activity_type:
            query["type"] = activity_type
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        if end_date:
            query.setdefault("timestamp", {})["$lte"] = end_date
        
        activities = await self.db.user_activities.find(
            query, {"_id": 0}
        ).sort("timestamp", -1).to_list(10000)
        
        if format == ExportFormat.CSV:
            export_data = self._to_csv(activities)
            content_type = "text/csv"
            filename = f"user_activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            export_data = {
                "export_info": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "record_count": len(activities)
                },
                "data": activities
            }
            content_type = "application/json"
            filename = f"user_activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return {
            "data": export_data,
            "content_type": content_type,
            "filename": filename,
            "record_count": len(activities)
        }
    
    async def export_revenue_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day",
        format: str = ExportFormat.JSON
    ) -> Dict[str, Any]:
        """Export revenue report with aggregations"""
        # Build date match
        date_match = {}
        if start_date:
            date_match["$gte"] = start_date.isoformat()
        if end_date:
            date_match["$lte"] = end_date.isoformat()
        
        match_stage = {"status": "SUCCESS"}
        if date_match:
            match_stage["createdAt"] = date_match
        
        # Group format based on period
        date_formats = {
            "day": "%Y-%m-%d",
            "week": "%Y-W%V",
            "month": "%Y-%m"
        }
        date_format = date_formats.get(group_by, "%Y-%m-%d")
        
        pipeline = [
            {"$match": match_stage},
            {"$addFields": {
                "createdDate": {"$dateFromString": {"dateString": "$createdAt"}}
            }},
            {"$group": {
                "_id": {"$dateToString": {"format": date_format, "date": "$createdDate"}},
                "total_revenue": {"$sum": "$amount"},
                "transaction_count": {"$sum": 1},
                "total_credits": {"$sum": "$credits"},
                "avg_order_value": {"$avg": "$amount"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        revenue_data = await self.db.orders.aggregate(pipeline).to_list(1000)
        
        # Format output
        formatted_data = [
            {
                "period": r["_id"],
                "total_revenue": round(r["total_revenue"], 2),
                "transaction_count": r["transaction_count"],
                "total_credits": r["total_credits"],
                "avg_order_value": round(r["avg_order_value"], 2)
            }
            for r in revenue_data
        ]
        
        # Calculate totals
        totals = {
            "total_revenue": sum(r["total_revenue"] for r in formatted_data),
            "total_transactions": sum(r["transaction_count"] for r in formatted_data),
            "total_credits_sold": sum(r["total_credits"] for r in formatted_data)
        }
        
        if format == ExportFormat.CSV:
            export_data = self._to_csv(formatted_data)
            content_type = "text/csv"
            filename = f"revenue_report_{group_by}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            export_data = {
                "export_info": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "group_by": group_by,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "totals": totals,
                "data": formatted_data
            }
            content_type = "application/json"
            filename = f"revenue_report_{group_by}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return {
            "data": export_data,
            "content_type": content_type,
            "filename": filename,
            "totals": totals
        }
    
    async def export_system_health(
        self,
        days: int = 30,
        format: str = ExportFormat.JSON
    ) -> Dict[str, Any]:
        """Export system health metrics"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Collect various health metrics
        health_data = {
            "auto_refunds": await self._get_refund_data(start_date),
            "self_healing_incidents": await self._get_incident_data(start_date),
            "job_statistics": await self._get_job_stats(start_date),
            "payment_statistics": await self._get_payment_stats(start_date)
        }
        
        if format == ExportFormat.CSV:
            # Flatten for CSV
            flat_data = []
            for category, items in health_data.items():
                for item in items if isinstance(items, list) else [items]:
                    if isinstance(item, dict):
                        item["category"] = category
                        flat_data.append(item)
            
            export_data = self._to_csv(flat_data)
            content_type = "text/csv"
            filename = f"system_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            export_data = {
                "export_info": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_days": days
                },
                "health_data": health_data
            }
            content_type = "application/json"
            filename = f"system_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return {
            "data": export_data,
            "content_type": content_type,
            "filename": filename
        }
    
    async def create_comprehensive_export(
        self,
        include_templates: bool = True,
        include_users: bool = True,
        include_revenue: bool = True,
        include_health: bool = True,
        days: int = 30
    ) -> Dict[str, Any]:
        """Create a comprehensive ZIP export with all data"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        exports = {}
        
        if include_templates:
            template_export = await self.export_template_analytics(
                start_date=start_date, include_details=True
            )
            exports["template_analytics.json"] = json.dumps(template_export["data"], indent=2, default=str)
        
        if include_revenue:
            revenue_export = await self.export_revenue_report(start_date=start_date)
            exports["revenue_report.json"] = json.dumps(revenue_export["data"], indent=2, default=str)
        
        if include_health:
            health_export = await self.export_system_health(days=days)
            exports["system_health.json"] = json.dumps(health_export["data"], indent=2, default=str)
        
        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in exports.items():
                zip_file.writestr(filename, content)
        
        zip_buffer.seek(0)
        
        return {
            "data": zip_buffer.read(),
            "content_type": "application/zip",
            "filename": f"comprehensive_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            "files_included": list(exports.keys())
        }
    
    def _calculate_summary(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        if not data:
            return {"total_records": 0}
        
        return {
            "total_records": len(data),
            "date_range": {
                "earliest": min((d.get("timestamp", "") for d in data), default=""),
                "latest": max((d.get("timestamp", "") for d in data), default="")
            }
        }
    
    def _to_csv(self, data: List[Dict]) -> str:
        """Convert list of dicts to CSV string"""
        if not data:
            return ""
        
        output = io.StringIO()
        
        # Get all unique keys
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())
        fieldnames = sorted(all_keys)
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    async def _get_refund_data(self, start_date: datetime) -> List[Dict]:
        """Get refund data for export"""
        return await self.db.auto_refund_logs.find(
            {"timestamp": {"$gte": start_date}}, {"_id": 0}
        ).to_list(1000)
    
    async def _get_incident_data(self, start_date: datetime) -> List[Dict]:
        """Get incident data for export"""
        return await self.db.self_healing_incidents.find(
            {"timestamp": {"$gte": start_date}}, {"_id": 0}
        ).to_list(1000)
    
    async def _get_job_stats(self, start_date: datetime) -> Dict[str, Any]:
        """Get job statistics"""
        pipeline = [
            {"$match": {"updatedAt": {"$gte": start_date.isoformat()}}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        stats = await self.db.genstudio_jobs.aggregate(pipeline).to_list(10)
        return {s["_id"]: s["count"] for s in stats}
    
    async def _get_payment_stats(self, start_date: datetime) -> Dict[str, Any]:
        """Get payment statistics"""
        pipeline = [
            {"$match": {"createdAt": {"$gte": start_date.isoformat()}}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total": {"$sum": "$amount"}
            }}
        ]
        stats = await self.db.orders.aggregate(pipeline).to_list(10)
        return {s["_id"]: {"count": s["count"], "total": s["total"]} for s in stats}
