#!/bin/sh
# pre-commit guard runner for the sp500-exec-comp repo.
#
# Install (one-time per checkout):
#   cp scripts/pre-commit-guards.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
#
# Runs both committed guards on every commit:
#   1. scripts/check_metadata_consistency.py       - data truthfulness (recounts
#      every metadata count field against the live JSONs; blocks on drift).
#   2. scripts/check_methodology_buttons.py --static-only - the static half
#      (A1-A6) of the methodology-buttons regression guard: all chart-title
#      rewrites go through _setTitleLabel so the methodology info buttons
#      survive chart re-renders (the 2026-10-05 GER-button-wipe bug class).
#      The render half (R1-R6) stays iteration-run-only: ~25s Chromium startup.
#
# Added by the 2026-10-05 15:30 iteration, closing the 14:10 run's queued
# candidate: "wire the new guard's static half into the pre-commit hook".
# Static half runs in ~0.25s, so the hook stays fast.
set -u
TOP="$(git rev-parse --show-toplevel)"
"$TOP/scripts/check_metadata_consistency.py" || exit 1
exec "$TOP/scripts/check_methodology_buttons.py" --static-only
