#!/bin/bash
# Test runner for Cloud Run Job.
# Env vars expected:
#   GOOGLE_API_KEY      — Gemini API key (for structural tests)
#   GEMINI_MODEL        — e.g. gemini-2.5-flash
#   API_BASE_URL        — e.g. https://agent-service-xxx.run.app   (no /ui)
#   UI_BASE_URL         — e.g. https://agent-service-xxx.run.app/ui
#   GCS_REPORT_BUCKET   — GCS bucket name for Allure HTML report
#   SESSION_DB_PATH     — optional, defaults to /tmp/adk_sessions.db

set -o pipefail

RESULTS_DIR="/tmp/allure-results"
REPORT_DIR="/tmp/allure-report"
OVERALL_EXIT=0

export SESSION_DB_PATH="${SESSION_DB_PATH:-/tmp/test_sessions.db}"
export TRACE_TO_CLOUD="false"
export TEST_BASE_URL="${API_BASE_URL}"

echo "============================================================"
echo " Lloyds Bank AI — Automated Test Suite"
echo " API  : ${API_BASE_URL}"
echo " UI   : ${UI_BASE_URL}"
echo " Model: ${GEMINI_MODEL}"
echo "============================================================"

# ── 1. Structural API tests (in-process, ~5s) ────────────────────────────
echo ""
echo ">>> [1/3] Structural API tests"
uv run pytest tests/test_api.py \
  -v --tb=short --alluredir="$RESULTS_DIR" \
  2>&1
STATUS=$?
[ $STATUS -ne 0 ] && OVERALL_EXIT=$STATUS && echo "FAILED: structural tests"

# ── 2. Integration tests (live API, ~30s) ────────────────────────────────
echo ""
echo ">>> [2/3] Integration tests  (target: ${API_BASE_URL})"
TEST_BASE_URL="${API_BASE_URL}" \
  uv run pytest tests/test_integration.py \
    -v --tb=short --alluredir="$RESULTS_DIR" \
    2>&1
STATUS=$?
[ $STATUS -ne 0 ] && OVERALL_EXIT=$STATUS && echo "FAILED: integration tests"

# ── 3. Playwright E2E tests (headless Chromium, ~100s) ───────────────────
echo ""
echo ">>> [3/3] Playwright E2E tests (target: ${UI_BASE_URL})"
TEST_BASE_URL="${UI_BASE_URL}" \
  uv run pytest tests/test_playwright.py \
    -v --tb=short --alluredir="$RESULTS_DIR" \
    2>&1
STATUS=$?
[ $STATUS -ne 0 ] && OVERALL_EXIT=$STATUS && echo "FAILED: playwright tests"

# ── Generate & upload Allure report ──────────────────────────────────────
echo ""
echo ">>> Generating Allure HTML report..."
allure generate "$RESULTS_DIR" -o "$REPORT_DIR" --clean 2>&1

if [ -n "$GCS_REPORT_BUCKET" ]; then
  RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo ">>> Uploading report to gs://${GCS_REPORT_BUCKET}/${RUN_TS}/ ..."
  uv run python upload_report.py "${GCS_REPORT_BUCKET}" "${REPORT_DIR}" "${RUN_TS}"
  uv run python upload_report.py "${GCS_REPORT_BUCKET}" "${REPORT_DIR}" "latest"
  echo ""
  echo "============================================================"
  echo " Allure report:"
  echo "   https://storage.googleapis.com/${GCS_REPORT_BUCKET}/latest/index.html"
  echo "============================================================"
fi

echo ""
if [ $OVERALL_EXIT -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "SOME TESTS FAILED — see output above"
fi

exit $OVERALL_EXIT
