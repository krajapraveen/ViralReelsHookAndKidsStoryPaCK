#!/usr/bin/env python3
"""
CreatorStudio AI - Master Automation Controller
Orchestrates all automation tasks and provides a unified control interface.
"""

import subprocess
import sys
import os
import json
import time
import signal
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add scripts to path
sys.path.insert(0, '/app/automation/scripts')

LOG_FILE = '/app/automation/logs/master_controller.log'
STATUS_FILE = '/app/automation/reports/automation_status.json'

# Import automation modules
from health_monitor import perform_health_check
from auto_recovery import run_recovery
from api_validator import run_validation
from database_maintenance import run_maintenance

class AutomationStatus:
    """Track automation status"""
    def __init__(self):
        self.status = {
            'running': True,
            'started_at': datetime.now().isoformat(),
            'last_health_check': None,
            'last_recovery': None,
            'last_validation': None,
            'last_maintenance': None,
            'health_status': 'unknown',
            'checks_performed': 0,
            'recoveries_performed': 0,
            'issues_fixed': 0
        }
    
    def update(self, key, value):
        self.status[key] = value
        self.save()
    
    def save(self):
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def get(self):
        return self.status

automation_status = AutomationStatus()

def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def run_health_check_cycle():
    """Run a health check cycle"""
    log("Running health check cycle...")
    try:
        report = perform_health_check()
        automation_status.update('last_health_check', datetime.now().isoformat())
        automation_status.update('health_status', report['status'])
        automation_status.status['checks_performed'] += 1
        
        if report['actions_taken']:
            automation_status.status['issues_fixed'] += len(report['actions_taken'])
            automation_status.status['recoveries_performed'] += 1
            automation_status.update('last_recovery', datetime.now().isoformat())
        
        automation_status.save()
        return report
    except Exception as e:
        log(f"Error in health check: {e}", 'ERROR')
        return None

def run_api_validation_cycle():
    """Run API validation"""
    log("Running API validation cycle...")
    try:
        report = run_validation()
        automation_status.update('last_validation', datetime.now().isoformat())
        return report
    except Exception as e:
        log(f"Error in API validation: {e}", 'ERROR')
        return None

def run_database_maintenance_cycle():
    """Run database maintenance"""
    log("Running database maintenance cycle...")
    try:
        report = run_maintenance()
        automation_status.update('last_maintenance', datetime.now().isoformat())
        return report
    except Exception as e:
        log(f"Error in database maintenance: {e}", 'ERROR')
        return None

def continuous_monitoring(health_interval=60, validation_interval=300, maintenance_interval=3600):
    """Run continuous monitoring with different intervals for each task"""
    
    last_health = 0
    last_validation = 0
    last_maintenance = 0
    
    log("Starting continuous monitoring...")
    log(f"  Health check interval: {health_interval}s")
    log(f"  API validation interval: {validation_interval}s")
    log(f"  Database maintenance interval: {maintenance_interval}s")
    
    while automation_status.status['running']:
        current_time = time.time()
        
        # Health check (most frequent)
        if current_time - last_health >= health_interval:
            run_health_check_cycle()
            last_health = current_time
        
        # API validation (less frequent)
        if current_time - last_validation >= validation_interval:
            run_api_validation_cycle()
            last_validation = current_time
        
        # Database maintenance (least frequent)
        if current_time - last_maintenance >= maintenance_interval:
            run_database_maintenance_cycle()
            last_maintenance = current_time
        
        time.sleep(10)  # Check every 10 seconds

class StatusHandler(BaseHTTPRequestHandler):
    """HTTP handler for status endpoint"""
    
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(automation_status.get(), indent=2).encode())
        elif self.path == '/health':
            status = automation_status.get()
            if status['health_status'] in ['healthy', 'unknown']:
                self.send_response(200)
            else:
                self.send_response(503)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': status['health_status']}).encode())
        elif self.path == '/trigger/health':
            threading.Thread(target=run_health_check_cycle).start()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'Health check triggered'}).encode())
        elif self.path == '/trigger/recovery':
            threading.Thread(target=run_recovery).start()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'Recovery triggered'}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

def start_status_server(port=9090):
    """Start HTTP status server"""
    server = HTTPServer(('0.0.0.0', port), StatusHandler)
    log(f"Status server started on port {port}")
    server.serve_forever()

def signal_handler(sig, frame):
    """Handle shutdown signal"""
    log("Received shutdown signal, stopping...")
    automation_status.update('running', False)
    sys.exit(0)

def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log("=" * 60)
    log("CreatorStudio AI - Master Automation Controller")
    log("=" * 60)
    
    # Run initial recovery to ensure everything is up
    log("Running initial system recovery...")
    run_recovery()
    
    # Start status server in background
    status_thread = threading.Thread(target=start_status_server, daemon=True)
    status_thread.start()
    
    # Start continuous monitoring
    try:
        continuous_monitoring(
            health_interval=60,      # Every 1 minute
            validation_interval=300,  # Every 5 minutes
            maintenance_interval=3600 # Every 1 hour
        )
    except KeyboardInterrupt:
        log("Shutting down...")

if __name__ == '__main__':
    main()
