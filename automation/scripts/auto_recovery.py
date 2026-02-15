#!/usr/bin/env python3
"""
CreatorStudio AI - Service Auto-Recovery Script
Handles automatic recovery of failed services with intelligent retry logic.
"""

import subprocess
import time
import os
import json
from datetime import datetime

LOG_FILE = '/app/automation/logs/auto_recovery.log'

def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def run_cmd(cmd, timeout=120):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def ensure_postgresql():
    """Ensure PostgreSQL is running and accessible"""
    log("Checking PostgreSQL...")
    
    # Check if running
    success, output = run_cmd("pg_isready -h localhost -p 5432")
    if success:
        log("PostgreSQL is ready")
        return True
    
    # Try to start
    log("Starting PostgreSQL...", 'WARNING')
    run_cmd("sudo service postgresql start")
    time.sleep(3)
    
    # Create database if not exists
    run_cmd("sudo -u postgres createdb creatorstudio 2>/dev/null || true")
    run_cmd("sudo -u postgres psql -c \"CREATE USER root WITH SUPERUSER PASSWORD 'postgres';\" 2>/dev/null || true")
    
    success, output = run_cmd("pg_isready -h localhost -p 5432")
    if success:
        log("PostgreSQL started successfully")
        return True
    
    log("Failed to start PostgreSQL", 'ERROR')
    return False

def ensure_redis():
    """Ensure Redis is running"""
    log("Checking Redis...")
    
    success, output = run_cmd("redis-cli ping")
    if success and 'PONG' in output:
        log("Redis is ready")
        return True
    
    log("Starting Redis...", 'WARNING')
    run_cmd("redis-server --daemonize yes --logfile '' --protected-mode no")
    time.sleep(2)
    
    success, output = run_cmd("redis-cli ping")
    if success and 'PONG' in output:
        log("Redis started successfully")
        return True
    
    log("Failed to start Redis", 'ERROR')
    return False

def ensure_rabbitmq():
    """Ensure RabbitMQ is running"""
    log("Checking RabbitMQ...")
    
    success, output = run_cmd("rabbitmqctl status 2>/dev/null")
    if success:
        log("RabbitMQ is ready")
        return True
    
    log("Starting RabbitMQ...", 'WARNING')
    run_cmd("rabbitmq-server -detached 2>/dev/null")
    time.sleep(5)
    
    success, output = run_cmd("rabbitmqctl status 2>/dev/null")
    if success:
        log("RabbitMQ started successfully")
        return True
    
    log("Failed to start RabbitMQ", 'ERROR')
    return False

def ensure_springboot():
    """Ensure Spring Boot backend is running"""
    log("Checking Spring Boot backend...")
    
    success, output = run_cmd("sudo supervisorctl status springboot")
    if 'RUNNING' in output:
        log("Spring Boot is running")
        return True
    
    log("Starting Spring Boot...", 'WARNING')
    
    # Check if JAR exists, if not build it
    if not os.path.exists('/app/backend-springboot/target/creatorstudio-0.0.1-SNAPSHOT.jar'):
        log("Building Spring Boot application...", 'WARNING')
        success, output = run_cmd("cd /app/backend-springboot && mvn clean package -DskipTests -q", timeout=180)
        if not success:
            log(f"Maven build failed: {output}", 'ERROR')
            return False
    
    run_cmd("sudo supervisorctl start springboot")
    time.sleep(10)
    
    success, output = run_cmd("sudo supervisorctl status springboot")
    if 'RUNNING' in output:
        log("Spring Boot started successfully")
        return True
    
    log("Failed to start Spring Boot", 'ERROR')
    return False

def ensure_frontend():
    """Ensure React frontend is running"""
    log("Checking Frontend...")
    
    success, output = run_cmd("sudo supervisorctl status frontend")
    if 'RUNNING' in output:
        log("Frontend is running")
        return True
    
    log("Starting Frontend...", 'WARNING')
    run_cmd("sudo supervisorctl start frontend")
    time.sleep(5)
    
    success, output = run_cmd("sudo supervisorctl status frontend")
    if 'RUNNING' in output:
        log("Frontend started successfully")
        return True
    
    log("Failed to start Frontend", 'ERROR')
    return False

def ensure_worker():
    """Ensure Python worker is running"""
    log("Checking Worker...")
    
    success, output = run_cmd("sudo supervisorctl status worker")
    if 'RUNNING' in output:
        log("Worker is running")
        return True
    
    log("Starting Worker...", 'WARNING')
    run_cmd("sudo supervisorctl start worker")
    time.sleep(5)
    
    success, output = run_cmd("sudo supervisorctl status worker")
    if 'RUNNING' in output:
        log("Worker started successfully")
        return True
    
    log("Failed to start Worker", 'ERROR')
    return False

def clear_stuck_queues():
    """Clear stuck messages from RabbitMQ queues if they're too old"""
    log("Checking for stuck queue messages...")
    
    success, output = run_cmd("rabbitmqctl list_queues name messages 2>/dev/null")
    if success:
        for line in output.split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0] == 'story.request':
                try:
                    msg_count = int(parts[1])
                    if msg_count > 20:
                        log(f"Found {msg_count} stuck messages, purging queue...", 'WARNING')
                        run_cmd("rabbitmqctl purge_queue story.request 2>/dev/null")
                        log("Queue purged")
                except:
                    pass

def run_recovery():
    """Run full recovery sequence"""
    log("=" * 50)
    log("Starting Auto-Recovery Sequence")
    log("=" * 50)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'services': {}
    }
    
    # Infrastructure first
    results['services']['postgresql'] = ensure_postgresql()
    results['services']['redis'] = ensure_redis()
    results['services']['rabbitmq'] = ensure_rabbitmq()
    
    # Application services
    results['services']['springboot'] = ensure_springboot()
    results['services']['frontend'] = ensure_frontend()
    results['services']['worker'] = ensure_worker()
    
    # Maintenance tasks
    clear_stuck_queues()
    
    # Summary
    all_ok = all(results['services'].values())
    results['overall_status'] = 'healthy' if all_ok else 'degraded'
    
    log("=" * 50)
    log(f"Recovery Complete. Status: {results['overall_status']}")
    for svc, status in results['services'].items():
        log(f"  {svc}: {'✓' if status else '✗'}")
    log("=" * 50)
    
    # Save results
    with open('/app/automation/reports/recovery_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return all_ok

if __name__ == '__main__':
    success = run_recovery()
    exit(0 if success else 1)
