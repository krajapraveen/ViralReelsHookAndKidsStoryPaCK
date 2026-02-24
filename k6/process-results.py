#!/usr/bin/env python3
"""
K6 Results Processor for Monitoring Dashboard Integration

Processes K6 JSON output and sends metrics to monitoring systems:
- Prometheus/Grafana via pushgateway
- InfluxDB
- Custom monitoring dashboards via webhook

Usage: python process-results.py results.json
"""

import json
import sys
import os
import requests
from datetime import datetime
from typing import Dict, Any

# Configuration from environment
PROMETHEUS_PUSHGATEWAY = os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'http://localhost:9091')
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'creatorstudio')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'k6_metrics')
WEBHOOK_URL = os.getenv('MONITORING_WEBHOOK_URL', '')
SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK_URL', '')


def load_k6_results(filepath: str) -> Dict[str, Any]:
    """Load K6 JSON results file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_key_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from K6 results"""
    metrics = data.get('metrics', {})
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'test_name': 'CreatorStudio Load Test',
        
        # Request metrics
        'http_requests_total': metrics.get('http_reqs', {}).get('values', {}).get('count', 0),
        'http_requests_rate': metrics.get('http_reqs', {}).get('values', {}).get('rate', 0),
        
        # Duration metrics
        'http_req_duration_avg': metrics.get('http_req_duration', {}).get('values', {}).get('avg', 0),
        'http_req_duration_p95': metrics.get('http_req_duration', {}).get('values', {}).get('p(95)', 0),
        'http_req_duration_p99': metrics.get('http_req_duration', {}).get('values', {}).get('p(99)', 0),
        'http_req_duration_max': metrics.get('http_req_duration', {}).get('values', {}).get('max', 0),
        
        # Error metrics
        'http_req_failed_count': metrics.get('http_req_failed', {}).get('values', {}).get('passes', 0),
        'http_req_failed_rate': metrics.get('http_req_failed', {}).get('values', {}).get('rate', 0),
        
        # Custom metrics
        'api_errors_total': metrics.get('api_errors', {}).get('values', {}).get('count', 0),
        'success_rate': metrics.get('success_rate', {}).get('values', {}).get('rate', 1),
        'api_latency_p95': metrics.get('api_latency', {}).get('values', {}).get('p(95)', 0),
        
        # VU metrics
        'vus_max': metrics.get('vus_max', {}).get('values', {}).get('max', 0),
        'iterations_total': metrics.get('iterations', {}).get('values', {}).get('count', 0),
        
        # Thresholds
        'thresholds_passed': all(
            t.get('ok', False) for t in data.get('thresholds', {}).values()
        )
    }


def push_to_prometheus(metrics: Dict[str, Any]) -> bool:
    """Push metrics to Prometheus Pushgateway"""
    try:
        # Format metrics for Prometheus
        prometheus_metrics = f"""
# HELP k6_http_requests_total Total HTTP requests made
# TYPE k6_http_requests_total counter
k6_http_requests_total {metrics['http_requests_total']}

# HELP k6_http_req_duration_avg Average HTTP request duration in ms
# TYPE k6_http_req_duration_avg gauge
k6_http_req_duration_avg {metrics['http_req_duration_avg']}

# HELP k6_http_req_duration_p95 95th percentile HTTP request duration in ms
# TYPE k6_http_req_duration_p95 gauge
k6_http_req_duration_p95 {metrics['http_req_duration_p95']}

# HELP k6_http_req_failed_rate HTTP request failure rate
# TYPE k6_http_req_failed_rate gauge
k6_http_req_failed_rate {metrics['http_req_failed_rate']}

# HELP k6_success_rate Overall success rate
# TYPE k6_success_rate gauge
k6_success_rate {metrics['success_rate']}

# HELP k6_api_latency_p95 95th percentile API latency in ms
# TYPE k6_api_latency_p95 gauge
k6_api_latency_p95 {metrics['api_latency_p95']}

# HELP k6_thresholds_passed Whether all thresholds passed
# TYPE k6_thresholds_passed gauge
k6_thresholds_passed {1 if metrics['thresholds_passed'] else 0}
"""
        
        response = requests.post(
            f"{PROMETHEUS_PUSHGATEWAY}/metrics/job/k6_load_test",
            data=prometheus_metrics,
            headers={'Content-Type': 'text/plain'}
        )
        
        print(f"Prometheus push: {response.status_code}")
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error pushing to Prometheus: {e}")
        return False


def push_to_influxdb(metrics: Dict[str, Any]) -> bool:
    """Push metrics to InfluxDB"""
    if not INFLUXDB_TOKEN:
        print("InfluxDB token not set, skipping")
        return False
    
    try:
        # Format for InfluxDB line protocol
        timestamp_ns = int(datetime.utcnow().timestamp() * 1e9)
        
        line_protocol = f"""k6_metrics,test=creatorstudio_load http_requests={metrics['http_requests_total']}i,duration_avg={metrics['http_req_duration_avg']},duration_p95={metrics['http_req_duration_p95']},failed_rate={metrics['http_req_failed_rate']},success_rate={metrics['success_rate']},api_latency_p95={metrics['api_latency_p95']},thresholds_passed={1 if metrics['thresholds_passed'] else 0}i {timestamp_ns}"""
        
        response = requests.post(
            f"{INFLUXDB_URL}/api/v2/write?org={INFLUXDB_ORG}&bucket={INFLUXDB_BUCKET}&precision=ns",
            data=line_protocol,
            headers={
                'Authorization': f'Token {INFLUXDB_TOKEN}',
                'Content-Type': 'text/plain'
            }
        )
        
        print(f"InfluxDB push: {response.status_code}")
        return response.status_code == 204
        
    except Exception as e:
        print(f"Error pushing to InfluxDB: {e}")
        return False


def send_webhook_notification(metrics: Dict[str, Any]) -> bool:
    """Send metrics to custom monitoring webhook"""
    if not WEBHOOK_URL:
        print("Webhook URL not set, skipping")
        return False
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json={
                'event': 'k6_load_test_complete',
                'timestamp': metrics['timestamp'],
                'metrics': metrics,
                'summary': {
                    'total_requests': metrics['http_requests_total'],
                    'avg_response_time': round(metrics['http_req_duration_avg'], 2),
                    'p95_response_time': round(metrics['http_req_duration_p95'], 2),
                    'error_rate': round(metrics['http_req_failed_rate'] * 100, 2),
                    'success_rate': round(metrics['success_rate'] * 100, 2),
                    'thresholds_passed': metrics['thresholds_passed']
                }
            },
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Webhook notification: {response.status_code}")
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return False


def send_slack_notification(metrics: Dict[str, Any]) -> bool:
    """Send load test results to Slack"""
    if not SLACK_WEBHOOK:
        print("Slack webhook not set, skipping")
        return False
    
    try:
        status_emoji = "✅" if metrics['thresholds_passed'] else "❌"
        status_text = "PASSED" if metrics['thresholds_passed'] else "FAILED"
        
        slack_message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} K6 Load Test Results - {status_text}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Requests:*\n{metrics['http_requests_total']:,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Request Rate:*\n{metrics['http_requests_rate']:.2f}/s"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg Response:*\n{metrics['http_req_duration_avg']:.2f}ms"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*P95 Response:*\n{metrics['http_req_duration_p95']:.2f}ms"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Error Rate:*\n{metrics['http_req_failed_rate']*100:.2f}%"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Success Rate:*\n{metrics['success_rate']*100:.2f}%"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Test completed at {metrics['timestamp']}"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            SLACK_WEBHOOK,
            json=slack_message,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Slack notification: {response.status_code}")
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending Slack notification: {e}")
        return False


def generate_report(metrics: Dict[str, Any]) -> str:
    """Generate human-readable report"""
    status = "✅ PASSED" if metrics['thresholds_passed'] else "❌ FAILED"
    
    report = f"""
╔══════════════════════════════════════════════════════════════════╗
║              K6 LOAD TEST RESULTS - {status}                 
╠══════════════════════════════════════════════════════════════════╣
║  Test: {metrics['test_name']}
║  Time: {metrics['timestamp']}
╠══════════════════════════════════════════════════════════════════╣
║  REQUEST METRICS
║  ────────────────────────────────────────────────────────────────
║  Total Requests:     {metrics['http_requests_total']:>10,}
║  Request Rate:       {metrics['http_requests_rate']:>10.2f}/s
║  Max VUs:            {metrics['vus_max']:>10}
║  Total Iterations:   {metrics['iterations_total']:>10,}
╠══════════════════════════════════════════════════════════════════╣
║  RESPONSE TIMES
║  ────────────────────────────────────────────────────────────────
║  Average:            {metrics['http_req_duration_avg']:>10.2f}ms
║  P95:                {metrics['http_req_duration_p95']:>10.2f}ms
║  P99:                {metrics['http_req_duration_p99']:>10.2f}ms
║  Max:                {metrics['http_req_duration_max']:>10.2f}ms
╠══════════════════════════════════════════════════════════════════╣
║  ERROR METRICS
║  ────────────────────────────────────────────────────────────────
║  Failed Requests:    {metrics['http_req_failed_count']:>10}
║  Failure Rate:       {metrics['http_req_failed_rate']*100:>10.2f}%
║  Success Rate:       {metrics['success_rate']*100:>10.2f}%
║  API Errors:         {metrics['api_errors_total']:>10}
╠══════════════════════════════════════════════════════════════════╣
║  THRESHOLDS: {status}
╚══════════════════════════════════════════════════════════════════╝
"""
    return report


def save_metrics_to_file(metrics: Dict[str, Any], filepath: str = 'processed_metrics.json'):
    """Save processed metrics to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python process-results.py <results.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    print(f"Processing K6 results from: {results_file}")
    
    # Load and process results
    raw_data = load_k6_results(results_file)
    metrics = extract_key_metrics(raw_data)
    
    # Generate and print report
    report = generate_report(metrics)
    print(report)
    
    # Save processed metrics
    save_metrics_to_file(metrics)
    
    # Push to monitoring systems
    print("\nPushing metrics to monitoring systems...")
    push_to_prometheus(metrics)
    push_to_influxdb(metrics)
    send_webhook_notification(metrics)
    send_slack_notification(metrics)
    
    # Exit with appropriate code
    sys.exit(0 if metrics['thresholds_passed'] else 1)


if __name__ == '__main__':
    main()
