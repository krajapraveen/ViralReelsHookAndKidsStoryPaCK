#!/usr/bin/env python3
"""
CreatorStudio AI - API Endpoint Validator
Validates all API endpoints are working correctly with automated testing.
"""

import requests
import json
import time
import os
from datetime import datetime

API_BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://subscription-gateway-1.preview.emergentagent.com')
LOG_FILE = '/app/automation/logs/api_validation.log'
REPORT_FILE = '/app/automation/reports/api_validation_report.json'

# Test credentials
TEST_USER = {
    'email': 'automation_test@creatorstudio.ai',
    'password': 'AutoTest@123',
    'name': 'Automation Test User'
}

def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def get_auth_token():
    """Get authentication token, creating test user if needed"""
    # Try login first
    try:
        resp = requests.post(f"{API_BASE_URL}/api/auth/login", 
                           json={'email': TEST_USER['email'], 'password': TEST_USER['password']},
                           timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'token' in data:
                return data['token']
    except:
        pass
    
    # Try to register
    try:
        resp = requests.post(f"{API_BASE_URL}/api/auth/register",
                           json=TEST_USER,
                           timeout=10)
        if resp.status_code == 200:
            # Login after registration
            resp = requests.post(f"{API_BASE_URL}/api/auth/login",
                               json={'email': TEST_USER['email'], 'password': TEST_USER['password']},
                               timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if 'token' in data:
                    return data['token']
    except:
        pass
    
    return None

def validate_endpoint(endpoint, method='GET', data=None, token=None, expected_status=None):
    """Validate a single endpoint"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        start_time = time.time()
        
        if method == 'GET':
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            resp = requests.post(url, json=data, headers=headers, timeout=30)
        elif method == 'PUT':
            resp = requests.put(url, json=data, headers=headers, timeout=30)
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=30)
        
        response_time = (time.time() - start_time) * 1000  # ms
        
        # Determine if successful
        if expected_status:
            success = resp.status_code == expected_status
        else:
            success = resp.status_code < 500
        
        return {
            'endpoint': endpoint,
            'method': method,
            'status_code': resp.status_code,
            'response_time_ms': round(response_time, 2),
            'success': success,
            'error': None
        }
    
    except requests.exceptions.Timeout:
        return {
            'endpoint': endpoint,
            'method': method,
            'status_code': 0,
            'response_time_ms': 30000,
            'success': False,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'endpoint': endpoint,
            'method': method,
            'status_code': 0,
            'response_time_ms': 0,
            'success': False,
            'error': str(e)
        }

def run_validation():
    """Run full API validation"""
    log("Starting API validation...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'base_url': API_BASE_URL,
        'results': [],
        'summary': {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'avg_response_time': 0
        }
    }
    
    # Get auth token
    token = get_auth_token()
    if not token:
        log("Warning: Could not get auth token, some tests may fail", 'WARNING')
    
    # Define test cases
    test_cases = [
        # Public endpoints
        {'endpoint': '/api/auth/login', 'method': 'POST', 'data': {'email': 'test@test.com', 'password': 'test'}, 'auth': False},
        {'endpoint': '/api/payments/products', 'method': 'GET', 'auth': False},
        {'endpoint': '/api/payments/currencies', 'method': 'GET', 'auth': False},
        
        # Protected endpoints (require auth)
        {'endpoint': '/api/auth/me', 'method': 'GET', 'auth': True},
        {'endpoint': '/api/credits/balance', 'method': 'GET', 'auth': True},
        {'endpoint': '/api/credits/ledger?page=0&size=10', 'method': 'GET', 'auth': True},
        {'endpoint': '/api/generate/generations?page=0&size=10', 'method': 'GET', 'auth': True},
        {'endpoint': '/api/payments/history?page=0&size=10', 'method': 'GET', 'auth': True},
        {'endpoint': '/api/privacy/my-data', 'method': 'GET', 'auth': True},
        {'endpoint': '/api/features?page=0&size=10', 'method': 'GET', 'auth': True},
    ]
    
    total_response_time = 0
    
    for test in test_cases:
        auth_token = token if test.get('auth', False) else None
        result = validate_endpoint(
            test['endpoint'],
            test.get('method', 'GET'),
            test.get('data'),
            auth_token
        )
        
        report['results'].append(result)
        report['summary']['total'] += 1
        
        if result['success']:
            report['summary']['passed'] += 1
            log(f"✓ {test['method']} {test['endpoint']} - {result['status_code']} ({result['response_time_ms']}ms)")
        else:
            report['summary']['failed'] += 1
            log(f"✗ {test['method']} {test['endpoint']} - {result['status_code']} - {result.get('error', 'Failed')}", 'ERROR')
        
        total_response_time += result['response_time_ms']
    
    # Calculate average response time
    if report['summary']['total'] > 0:
        report['summary']['avg_response_time'] = round(total_response_time / report['summary']['total'], 2)
    
    # Overall status
    pass_rate = (report['summary']['passed'] / report['summary']['total']) * 100 if report['summary']['total'] > 0 else 0
    report['summary']['pass_rate'] = round(pass_rate, 1)
    report['summary']['status'] = 'healthy' if pass_rate >= 80 else 'degraded' if pass_rate >= 50 else 'critical'
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    log(f"Validation complete. Pass rate: {pass_rate:.1f}% ({report['summary']['passed']}/{report['summary']['total']})")
    log(f"Average response time: {report['summary']['avg_response_time']}ms")
    
    return report

if __name__ == '__main__':
    report = run_validation()
    print(json.dumps(report['summary'], indent=2))
