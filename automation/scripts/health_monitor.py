#!/usr/bin/env python3
"""
CreatorStudio AI - Comprehensive Health Monitor & Auto-Healer
This script monitors all services and automatically fixes issues.
"""

import subprocess
import requests
import time
import json
import os
import sys
from datetime import datetime
import psycopg2
import redis

# Configuration
API_BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://studio-audit.preview.emergentagent.com')
LOG_FILE = '/app/automation/logs/health_monitor.log'
REPORT_FILE = '/app/automation/reports/health_report.json'

# Service definitions
SERVICES = {
    'springboot': {
        'name': 'Spring Boot Backend',
        'check_url': f'{API_BASE_URL}/api/health',
        'supervisor_name': 'springboot',
        'port': 8001,
        'critical': True
    },
    'frontend': {
        'name': 'React Frontend',
        'check_url': API_BASE_URL,
        'supervisor_name': 'frontend',
        'port': 3000,
        'critical': True
    },
    'worker': {
        'name': 'Python AI Worker',
        'check_url': 'http://localhost:5000/health',
        'supervisor_name': 'worker',
        'port': 5000,
        'critical': True
    }
}

def log(message, level='INFO'):
    """Log message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def run_command(cmd, timeout=60):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def check_service_http(url, timeout=10):
    """Check if HTTP service is responding"""
    try:
        response = requests.get(url, timeout=timeout, verify=False)
        return response.status_code < 500, response.status_code
    except:
        return False, 0

def check_supervisor_status(service_name):
    """Check supervisor service status"""
    success, output = run_command(f"sudo supervisorctl status {service_name}")
    if 'RUNNING' in output:
        return True, 'RUNNING'
    elif 'STOPPED' in output:
        return False, 'STOPPED'
    elif 'FATAL' in output:
        return False, 'FATAL'
    else:
        return False, 'UNKNOWN'

def restart_service(service_name):
    """Restart a supervisor service"""
    log(f"Restarting service: {service_name}", 'WARNING')
    success, output = run_command(f"sudo supervisorctl restart {service_name}")
    time.sleep(5)  # Wait for service to start
    return success

def check_postgresql():
    """Check PostgreSQL database connectivity"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="creatorstudio",
            user="root",
            password="postgres"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

def start_postgresql():
    """Start PostgreSQL service"""
    log("Starting PostgreSQL...", 'WARNING')
    run_command("sudo service postgresql start")
    time.sleep(3)
    return check_postgresql()[0]

def check_redis():
    """Check Redis connectivity"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

def start_redis():
    """Start Redis service"""
    log("Starting Redis...", 'WARNING')
    run_command("redis-server --daemonize yes --logfile '' --protected-mode no")
    time.sleep(2)
    return check_redis()[0]

def check_rabbitmq():
    """Check RabbitMQ connectivity"""
    success, output = run_command("rabbitmqctl list_queues 2>/dev/null")
    return success and 'story' in output.lower(), output

def start_rabbitmq():
    """Start RabbitMQ service"""
    log("Starting RabbitMQ...", 'WARNING')
    run_command("rabbitmq-server -detached")
    time.sleep(5)
    return check_rabbitmq()[0]

def check_queue_health():
    """Check if message queues have stuck messages"""
    success, output = run_command("rabbitmqctl list_queues 2>/dev/null | grep story.request")
    if success and output:
        try:
            parts = output.strip().split()
            if len(parts) >= 2:
                msg_count = int(parts[1])
                return msg_count < 10, msg_count  # Alert if more than 10 stuck messages
        except:
            pass
    return True, 0

def rebuild_springboot():
    """Rebuild and restart Spring Boot if needed"""
    log("Rebuilding Spring Boot application...", 'WARNING')
    success, output = run_command("cd /app/backend-springboot && mvn clean package -DskipTests -q", timeout=180)
    if success:
        restart_service('springboot')
        time.sleep(10)
        return check_service_http(f'{API_BASE_URL}/api/health')[0]
    return False

def validate_api_endpoints():
    """Validate critical API endpoints are working"""
    endpoints = [
        ('/api/auth/login', 'POST', {'email': 'test@test.com', 'password': 'test'}),
        ('/api/payments/products', 'GET', None),
    ]
    
    results = {}
    for endpoint, method, data in endpoints:
        url = f"{API_BASE_URL}{endpoint}"
        try:
            if method == 'GET':
                resp = requests.get(url, timeout=10)
            else:
                resp = requests.post(url, json=data, timeout=10)
            results[endpoint] = resp.status_code < 500
        except:
            results[endpoint] = False
    
    return results

def perform_health_check():
    """Perform comprehensive health check"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'services': {},
        'infrastructure': {},
        'actions_taken': [],
        'issues': []
    }
    
    # Check infrastructure
    log("Checking infrastructure...")
    
    # PostgreSQL
    pg_ok, pg_msg = check_postgresql()
    report['infrastructure']['postgresql'] = {'status': 'up' if pg_ok else 'down', 'message': pg_msg}
    if not pg_ok:
        report['issues'].append('PostgreSQL is down')
        if start_postgresql():
            report['actions_taken'].append('Started PostgreSQL')
            log("PostgreSQL started successfully", 'INFO')
        else:
            report['status'] = 'critical'
            log("Failed to start PostgreSQL", 'ERROR')
    
    # Redis
    redis_ok, redis_msg = check_redis()
    report['infrastructure']['redis'] = {'status': 'up' if redis_ok else 'down', 'message': redis_msg}
    if not redis_ok:
        report['issues'].append('Redis is down')
        if start_redis():
            report['actions_taken'].append('Started Redis')
            log("Redis started successfully", 'INFO')
        else:
            report['status'] = 'degraded'
            log("Failed to start Redis", 'ERROR')
    
    # RabbitMQ
    rmq_ok, rmq_msg = check_rabbitmq()
    report['infrastructure']['rabbitmq'] = {'status': 'up' if rmq_ok else 'down'}
    if not rmq_ok:
        report['issues'].append('RabbitMQ is down')
        if start_rabbitmq():
            report['actions_taken'].append('Started RabbitMQ')
            log("RabbitMQ started successfully", 'INFO')
        else:
            report['status'] = 'degraded'
            log("Failed to start RabbitMQ", 'ERROR')
    
    # Check application services
    log("Checking application services...")
    
    for service_key, service_config in SERVICES.items():
        log(f"Checking {service_config['name']}...")
        
        # Check supervisor status
        sup_ok, sup_status = check_supervisor_status(service_config['supervisor_name'])
        
        # Check HTTP health
        http_ok, http_code = check_service_http(service_config['check_url'])
        
        service_healthy = sup_ok and http_ok
        
        report['services'][service_key] = {
            'name': service_config['name'],
            'supervisor_status': sup_status,
            'http_status': http_code,
            'healthy': service_healthy
        }
        
        if not service_healthy:
            report['issues'].append(f"{service_config['name']} is unhealthy")
            
            # Try to restart
            if restart_service(service_config['supervisor_name']):
                time.sleep(5)
                # Re-check
                http_ok, http_code = check_service_http(service_config['check_url'])
                if http_ok:
                    report['actions_taken'].append(f"Restarted {service_config['name']} successfully")
                    report['services'][service_key]['healthy'] = True
                    log(f"{service_config['name']} recovered after restart", 'INFO')
                else:
                    if service_config['critical']:
                        report['status'] = 'critical'
                    log(f"{service_config['name']} failed to recover", 'ERROR')
            else:
                if service_config['critical']:
                    report['status'] = 'critical'
                log(f"Failed to restart {service_config['name']}", 'ERROR')
    
    # Check for stuck queue messages
    queue_ok, msg_count = check_queue_health()
    report['infrastructure']['queue_messages'] = msg_count
    if not queue_ok:
        report['issues'].append(f'Queue has {msg_count} stuck messages')
        # Restart worker to process stuck messages
        restart_service('worker')
        report['actions_taken'].append('Restarted worker due to stuck messages')
    
    # Validate API endpoints
    log("Validating API endpoints...")
    api_results = validate_api_endpoints()
    report['api_validation'] = api_results
    
    # Final status determination
    critical_services = ['springboot', 'frontend']
    for svc in critical_services:
        if svc in report['services'] and not report['services'][svc]['healthy']:
            report['status'] = 'critical'
    
    if report['status'] == 'healthy' and report['issues']:
        report['status'] = 'degraded'
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    log(f"Health check completed. Status: {report['status']}")
    log(f"Issues: {len(report['issues'])}, Actions taken: {len(report['actions_taken'])}")
    
    return report

def continuous_monitor(interval=60):
    """Run continuous monitoring"""
    log("Starting continuous health monitoring...")
    
    while True:
        try:
            report = perform_health_check()
            
            if report['status'] == 'critical':
                log("CRITICAL: System is in critical state!", 'ERROR')
            elif report['status'] == 'degraded':
                log("WARNING: System is degraded", 'WARNING')
            else:
                log("System is healthy", 'INFO')
            
        except Exception as e:
            log(f"Error during health check: {str(e)}", 'ERROR')
        
        time.sleep(interval)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        continuous_monitor(interval=60)
    else:
        report = perform_health_check()
        print(json.dumps(report, indent=2))
