#!/usr/bin/env bash
# Runs every test. Exits nonzero if any suite fails. Usage: bash tests/run_all.sh
# Gates: tuned set >= 95%, each holdout >= 85%, zero complex (deep or max) tasks routed to fast.
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"; rc=0
echo "### Classification (tuned set / holdout 1 / holdout 2)"
for pair in run_tests.py:95 run_holdout.py:85 run_holdout2.py:85; do
  f="${pair%%:*}"; min="${pair##*:}"
  out=$("$PY" "$f" "$min"); code=$?
  echo "$out" | grep -E "^(TOTAL|GATE)| (COSTLY|QUALITY RISK)"
  if [ $code -ne 0 ]; then echo "FAIL $f (gate: >= $min%, no complex task to fast)"; rc=1; fi
done
echo "### On/off switch"; "$PY" toggle.py || { echo "FAIL on/off switch"; rc=1; }
echo "### Robustness"; bash robustness.sh || { echo "FAIL robustness"; rc=1; }
echo "### Performance"; HOME=/tmp/rh "$PY" perf.py || { echo "FAIL performance"; rc=1; }
[ $rc -eq 0 ] && echo "ALL SUITES PASSED" || echo "SOME SUITES FAILED"
exit $rc
