#!/usr/bin/env bash
# Runs every test. Usage: bash tests/run_all.sh
cd "$(dirname "$0")"
echo "### Classification (tuned set / holdout 1 / holdout 2)"
for f in run_tests.py run_holdout.py run_holdout2.py; do python3 $f | grep TOTAL; done
echo "### Robustness"; bash robustness.sh
echo "### Performance"; HOME=/tmp/rh python3 perf.py
