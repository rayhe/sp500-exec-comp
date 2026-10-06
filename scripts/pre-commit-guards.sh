#!/bin/sh
# pre-commit guard runner for the sp500-exec-comp repo.
#
# Install (one-time per checkout):
#   cp scripts/pre-commit-guards.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
#   (the hook is a COPY - re-copy after editing this file)
#
# Runs on every commit:
#   1. scripts/check_metadata_consistency.py (always) - data truthfulness
#      gate: recounts every metadata count field against the live JSONs and
#      blocks the commit on drift.
#   2. Every other scripts/check_*.py that implements a --static-only mode,
#      auto-discovered (see CONTRACT). Each runs as `script --static-only`.
#
# CONTRACT for adding a new static guard (no hook edit needed):
#   - name it scripts/check_<thing>.py
#   - honor "--static-only" in its argv handling. The runner greps the
#     script SOURCE for one of:
#         "--static-only" in sys.argv
#         '--static-only' in sys.argv
#         add_argument("--static-only" ...) / add_argument('--static-only' ...)
#     A docstring that merely MENTIONS --static-only does NOT opt in.
#   - exit 0 = pass; 1 = fail (blocks the commit); 2 = infra problem
#     (missing binary, no network) - treated as a pass-with-warning so a
#     broken laptop does not wedge every commit. (Guards that must never
#     be skipped on infra failure should say so in their header and exit 1.)
#   - keep the static half fast (<2s). Heavy render/browser halves stay
#     iteration-run-only behind the default (no-flag) invocation.
#
# History:
#   2026-10-05 15:30 - created with two hardcoded guards (metadata +
#     methodology-buttons --static-only).
#   2026-10-05 18:00 - generalized to auto-discovery per the 15:38 run's
#     queued candidate ("extend the pre-commit wrapper to future
#     static-only guards"); exit-2 infra rule documented.
set -u
TOP="$(git rev-parse --show-toplevel)"
"$TOP/scripts/check_metadata_consistency.py" || exit 1
FOUND=0
for g in "$TOP"/scripts/check_*.py; do
  [ -f "$g" ] || continue
  case "$g" in
    */check_metadata_consistency.py) continue ;;  # always-run gate above
  esac
  if grep -q -- '"--static-only" in sys.argv' "$g" \
    || grep -q -- "'--static-only' in sys.argv" "$g" \
    || grep -qE "add_argument\(.--static-only" "$g"; then
    FOUND=1
    "$g" --static-only
    rc=$?
    if [ "$rc" -eq 1 ]; then exit 1; fi
    if [ "$rc" -eq 2 ]; then echo "WARN: $g --static-only infra problem (exit 2), not blocking"; fi
  fi
done
[ "$FOUND" -eq 1 ] || echo "WARN: no --static-only guards discovered under scripts/check_*.py"
exit 0
