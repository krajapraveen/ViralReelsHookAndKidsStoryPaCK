#!/usr/bin/env python3
"""
CreatorStudio AI - Database Health & Maintenance Script
Handles database health checks, cleanup, and optimization.
"""

import psycopg2
from psycopg2 import sql
import json
import os
from datetime import datetime, timedelta

LOG_FILE = '/app/automation/logs/database_maintenance.log'
REPORT_FILE = '/app/automation/reports/database_report.json'

DB_CONFIG = {
    'host': 'localhost',
    'database': 'creatorstudio',
    'user': 'root',
    'password': 'postgres'
}

def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def get_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def check_database_health():
    """Check database connectivity and health"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check connectivity
        cursor.execute("SELECT 1")
        
        # Get database size
        cursor.execute("SELECT pg_size_pretty(pg_database_size('creatorstudio'))")
        db_size = cursor.fetchone()[0]
        
        # Get table counts
        cursor.execute("""
            SELECT relname, n_live_tup 
            FROM pg_stat_user_tables 
            ORDER BY n_live_tup DESC
        """)
        table_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return True, {
            'connected': True,
            'database_size': db_size,
            'table_counts': table_stats
        }
    except Exception as e:
        return False, {'error': str(e)}

def cleanup_old_sessions():
    """Clean up expired sessions older than 7 days"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clean up old user sessions
        cursor.execute("""
            DELETE FROM user_session 
            WHERE end_time IS NOT NULL 
            AND end_time < NOW() - INTERVAL '7 days'
        """)
        deleted_sessions = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        log(f"Cleaned up {deleted_sessions} old sessions")
        return deleted_sessions
    except Exception as e:
        log(f"Error cleaning sessions: {e}", 'ERROR')
        return 0

def cleanup_old_page_visits():
    """Clean up page visits older than 90 days"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM page_visit 
            WHERE timestamp < NOW() - INTERVAL '90 days'
        """)
        deleted_visits = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        log(f"Cleaned up {deleted_visits} old page visits")
        return deleted_visits
    except Exception as e:
        log(f"Error cleaning page visits: {e}", 'ERROR')
        return 0

def cleanup_failed_generations():
    """Clean up failed generations older than 30 days"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM generations 
            WHERE status = 'FAILED' 
            AND created_at < NOW() - INTERVAL '30 days'
        """)
        deleted_gens = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        log(f"Cleaned up {deleted_gens} old failed generations")
        return deleted_gens
    except Exception as e:
        log(f"Error cleaning generations: {e}", 'ERROR')
        return 0

def vacuum_tables():
    """Run VACUUM on tables to reclaim space"""
    try:
        conn = get_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            try:
                cursor.execute(f"VACUUM ANALYZE {table}")
                log(f"Vacuumed table: {table}")
            except Exception as e:
                log(f"Error vacuuming {table}: {e}", 'WARNING')
        
        conn.close()
        return True
    except Exception as e:
        log(f"Error during vacuum: {e}", 'ERROR')
        return False

def get_database_stats():
    """Get comprehensive database statistics"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # User count
        cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = cursor.fetchone()[0]
        
        # Generation counts
        cursor.execute("SELECT type, COUNT(*) FROM generations GROUP BY type")
        stats['generations_by_type'] = dict(cursor.fetchall())
        
        # Payment stats
        cursor.execute("SELECT status, COUNT(*) FROM payments GROUP BY status")
        stats['payments_by_status'] = dict(cursor.fetchall())
        
        # Recent activity (last 24h)
        cursor.execute("""
            SELECT COUNT(*) FROM generations 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        stats['generations_last_24h'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    except Exception as e:
        log(f"Error getting stats: {e}", 'ERROR')
        return {}

def run_maintenance():
    """Run full database maintenance"""
    log("=" * 50)
    log("Starting Database Maintenance")
    log("=" * 50)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'health': {},
        'cleanup': {},
        'stats': {}
    }
    
    # Health check
    healthy, health_data = check_database_health()
    report['health'] = health_data
    report['health']['status'] = 'healthy' if healthy else 'unhealthy'
    
    if healthy:
        log(f"Database healthy. Size: {health_data.get('database_size', 'unknown')}")
        
        # Run cleanup tasks
        report['cleanup']['sessions_deleted'] = cleanup_old_sessions()
        report['cleanup']['page_visits_deleted'] = cleanup_old_page_visits()
        report['cleanup']['failed_generations_deleted'] = cleanup_failed_generations()
        
        # Vacuum tables
        report['cleanup']['vacuum_completed'] = vacuum_tables()
        
        # Get stats
        report['stats'] = get_database_stats()
        
        log(f"Total users: {report['stats'].get('total_users', 0)}")
        log(f"Generations last 24h: {report['stats'].get('generations_last_24h', 0)}")
    else:
        log("Database unhealthy!", 'ERROR')
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    log("=" * 50)
    log("Database Maintenance Complete")
    log("=" * 50)
    
    return report

if __name__ == '__main__':
    report = run_maintenance()
    print(json.dumps(report, indent=2))
