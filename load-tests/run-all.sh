#!/bin/bash
# Load Test Runner — Executes all 3 phases sequentially
# Phase 1: Real LLM (100→500 VUs)
# Phase 2: Mock LLM (1K→10K VUs) 
# Phase 3: Spike Test (0→3K in 10s)

set -e

BASE_URL="${1:-https://trust-engine-5.preview.emergentagent.com}"
RESULTS_DIR="/app/load-tests/results"
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "  LOAD TEST RUNNER — $TIMESTAMP"
echo "  Target: $BASE_URL"
echo "=========================================="

run_phase() {
    local phase=$1
    local script=$2
    local description=$3
    
    echo ""
    echo "══════════════════════════════════════════"
    echo "  PHASE $phase: $description"
    echo "══════════════════════════════════════════"
    echo ""
    
    k6 run \
        --env BASE_URL="$BASE_URL" \
        --summary-trend-stats="avg,min,med,max,p(90),p(95),p(99)" \
        --out json="$RESULTS_DIR/phase${phase}_${TIMESTAMP}.json" \
        "$script" 2>&1 | tee "$RESULTS_DIR/phase${phase}_${TIMESTAMP}.log"
    
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "⚠️  PHASE $phase THRESHOLDS BREACHED"
        echo "    Review: $RESULTS_DIR/phase${phase}_${TIMESTAMP}.log"
    else
        echo ""
        echo "✅ PHASE $phase PASSED"
    fi
    
    echo ""
    echo "Results: $RESULTS_DIR/phase${phase}_${TIMESTAMP}.log"
    echo ""
    
    return $exit_code
}

# Phase 1 — Real LLM
echo ""
echo "⏳ Phase 1: Real LLM baseline (100→500 VUs)"
echo "   Duration: ~5 minutes"
echo "   Thresholds: p95 < 4s, errors < 5%"
echo ""
run_phase 1 "/app/load-tests/phase1-real-llm.js" "REAL LLM BASELINE (100→500 VUs)" || true

echo ""
echo "🔄 Switching to mock mode for Phase 2 & 3..."
echo ""

# Phase 2 — Mock infra stress
echo "⏳ Phase 2: Infrastructure stress (1K→10K VUs)"  
echo "   Duration: ~5 minutes"
echo "   Thresholds: p95 < 2s, errors < 5%"
echo ""
run_phase 2 "/app/load-tests/phase2-mock-infra.js" "MOCK INFRA STRESS (1K→10K VUs)" || true

# Phase 3 — Spike
echo "⏳ Phase 3: Spike test (0→3K in 10s)"
echo "   Duration: ~1 minute"
echo "   Thresholds: p95 < 3s, errors < 10%"
echo ""
run_phase 3 "/app/load-tests/phase3-spike.js" "VIRAL SPIKE (0→3K in 10s)" || true

echo ""
echo "=========================================="
echo "  ALL PHASES COMPLETE"
echo "  Results in: $RESULTS_DIR/"
echo "=========================================="
