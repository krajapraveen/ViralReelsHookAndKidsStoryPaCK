# Production Load Testing & Scale Readiness Runbook

## Overview
This runbook covers how to validate Visionary Suite at 10,000 concurrent users.
The system is **architecturally prepared** but NOT proven at scale until real production tests are run.

## Prerequisites
- k6 installed on a load generator machine (NOT the production server)
- Access to production/staging URL
- Sufficient network bandwidth from load gen machine
- MongoDB Atlas or equivalent with monitoring enabled

## Test Execution

### Step 1: Smoke Test (verify scripts work)
```bash
k6 run --env BASE_URL=https://your-production-url.com load-tests/mixed-workload.js
```
Expected: 10 VUs, 1 minute, all checks pass.

### Step 2: Ramp Tests (find breaking point)
Run each scenario progressively. Stop if thresholds fail.

```bash
# 100 users
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=smoke_100 load-tests/mixed-workload.js

# 500 users
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=ramp_500 load-tests/mixed-workload.js

# 1,000 users
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=ramp_1k load-tests/mixed-workload.js

# 3,000 users
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=ramp_3k load-tests/mixed-workload.js

# 5,000 users
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=ramp_5k load-tests/mixed-workload.js

# 10,000 users
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=ramp_10k load-tests/mixed-workload.js
```

### Step 3: Spike Test
```bash
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=spike load-tests/mixed-workload.js
```

### Step 4: Soak Test (1 hour)
```bash
k6 run --config load-tests/scenarios.json --env BASE_URL=https://your-url.com \
  -e K6_SCENARIO=soak_1h load-tests/mixed-workload.js
```

## Success Criteria

| Metric | Threshold |
|--------|-----------|
| p95 page latency (light endpoints) | <= 1.5s |
| p95 API latency (auth'd endpoints) | <= 2.5s |
| Queue acceptance latency | <= 2s |
| HTTP 5xx rate | < 0.5% |
| Timeout rate | < 1% |
| Failed jobs | < 1% |
| Broken/empty outputs | 0 |

## During Tests: Monitor

1. **System Health Dashboard**: `GET /api/admin/system-health/overview`
   - Queue depth per queue (should stay bounded)
   - Worker busy count (should not max out continuously)
   - Dead letter count (should not grow)
   - DB latency (should stay < 100ms)
   - Error rate (should stay < 0.5%)

2. **Queue Detail**: `GET /api/admin/system-health/queues`
   - Max wait time per queue (alert if > 60s for text, > 300s for video)

3. **Stuck Jobs**: `GET /api/admin/system-health/stuck-jobs`
   - Should be 0 during healthy operation

4. **MongoDB Monitoring** (Atlas or mongosh):
   - Connection count
   - Slow query log
   - Lock percentage
   - Replication lag (if replica set)

## Output Validation
After each test, verify:
1. Sample 10 completed jobs → outputs exist + non-empty
2. No cross-user leakage (job.userId matches output ownership)
3. Protected downloads still work
4. Watermarks still applied

## Autoscaling Recommendations

### Web/API (Horizontal Pod Autoscaler)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### Workers (KEDA ScaledObject per queue)
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: video-worker
spec:
  scaleTargetRef:
    name: video-worker
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: mongodb
    metadata:
      connectionStringFromEnv: MONGO_URL
      dbName: creatorstudio
      collection: genstudio_jobs
      query: '{"status":"QUEUED","queueType":"video"}'
      queryValue: "5"
```

### Connection Pool Tuning
- MongoDB: Set `maxPoolSize=100` per API instance
- Redis (if used): `maxclients 10000`

## Verdict Template

After running all tests, fill this:

```
INFRASTRUCTURE: [describe setup]
TEST PROFILE: [which scenarios ran]
MAX CONCURRENT: [peak VUs achieved]
p50/p95/p99: [latency numbers]
ERROR RATE: [actual %]
QUEUE HEALTH: [bounded/unbounded]
DEAD LETTER: [count]
OUTPUT VALIDATION: [pass/fail with sample count]
STUCK JOBS: [count]

VERDICT: [PASSES 10K | FAILS — with reasons]
RESIDUAL RISKS: [list]
```
