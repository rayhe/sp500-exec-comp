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
#   - rc 126/127 (Permission denied / command not found, i.e. the guard
#     lost its exec bit or its shebang broke) is a HARD FAIL: a guard
#     that cannot execute is indistinguishable from a guard that passes,
#     so it blocks the commit loudly instead of skipping silently.
#     check_guard_exec_bits.py additionally asserts the exec bit on
#     every check_*.py statically.
#   - keep the static half fast (<2s). Heavy render/browser halves stay
#     iteration-run-only behind the default (no-flag) invocation.
#
# History:
#   2026-10-05 15:30 - created with two hardcoded guards (metadata +
#     methodology-buttons --static-only).
#   2026-10-05 18:00 - generalized to auto-discovery per the 15:38 run's
#     queued candidate ("extend the pre-commit wrapper to future
#     static-only guards"); exit-2 infra rule documented.
#   2026-10-08 15:30 - rc 126/127 (exec-bit/shebang) is a hard fail instead
#     of a silent skip (silent-skip class: 03090dd, 2026-10-08
#     check_composition_fy_detail.py repair); check_guard_exec_bits.py
#     asserts the exec bit statically for every check_*.py.
#   2026-10-13 03:30 - check_hook_discovery_sync.py asserts every
#     scripts/check_*.py is actually SELECTED by the discovery greps above
#     (discovery-silent-skip class: a guard spelled differently from the
#     three grep patterns is executable yet never runs at commit).
#   2026-10-13 06:00 - check_remote_branch_sync.py asserts origin/main ==
#     origin/master at commit time (remote-branch desync class: a partial
#     push leaves the branches diverged with only the post-push eyeball
#     check as tripwire); network failure exits 2 (infra advisory).
#   2026-10-13 07:30 - check_postcommit_hook_sync.py asserts the installed
#     .git/hooks/post-commit is byte-identical to
#     scripts/post-commit-iteration-log.sh and executable
#     (post-commit-hook-sync class: the commit-logging backbone had no
#     sync assertion; a drifted/deleted/non-executable installed hook
#     would let commit-without-log-entry recur silently).
#   2026-10-13 10:00 - check_stub_home_capture.py asserts the canonical
#     iteration log actually contains the HEAD commit, by hash or by the
#     hook's subject-dedupe header match (post-commit-stub home-void
#     class: a commit made with HOME overridden - the IPv6-push recipe's
#     HOME=$TMPHOME - sends the hook's auto-stub into the throwaway temp
#     home silently; the manual backfill convention had no verifier).
#   2026-10-13 11:30 - check_orphaned_stub_detail.py asserts no bare
#     [AUTO-STUB] block stays detail-less past its backfill window
#     (orphaned-stub-detail class: check_stub_home_capture only asserts
#     the commit is PRESENT, so a bare stub with no backfilled detail
#     passed every guard silently; bare orphans older than 6h and within
#     7 days hard-fail, older ones print as advisories).
#   2026-10-13 14:00 - FAIL-OPEN-ENFORCEMENT in the runner loop plus
#     check_guard_exit_consistency.py (fail-open-exit class: the runner
#     blocked on exit code alone, so a guard printing a FAIL verdict yet
#     exiting 0 would false-green the commit; each guard's output is now
#     captured and a verdict with rc != 1 loud-blocks, rc 1 with no
#     verdict prints a diagnosability WARN; the new guard pins the
#     enforcement in the hook source (S1) and proves verdict ==> rc==1
#     dynamically over the suite in full mode (S2)).
#   2026-10-13 15:30 - check_log_prose_numbers.py asserts the latest full
#     iteration-log entry's "- Data:" bullet numbers match the data files
#     when it asserts "Recomputed from data files" (log-prose number-drift
#     class: per-run entries hand-write the headline audit numbers with
#     only the standing recompute-each-run hand-convention as tripwire; a
#     typo or stale copy-paste would make the audit trail lie with no
#     verifier). Companies/rows, verified_total, the DEF 14A-verified
#     percentage, peer nodes/edges, PvP companies/company-years,
#     enriched_count, and last_dq_repair are each checked when claimed;
#     bullets without the recompute marker print a WARN advisory only.
#   2026-10-13 18:00 - check_canary_freshness.py asserts the last full
#     drift-canary run is within 48h at commit time (watchdog-staleness
#     class: the canary's --check-stale mode was documented "cheap enough
#     for a scheduled drift check" yet invoked by nothing; the full-render
#     re-run cadence lived only in the iteration log's hand-written
#     next-run candidates list). Missing/unreadable state -> exit 2 infra
#     advisory (a deleted state file must not wedge commits); stale ->
#     HARD FAIL naming the re-run command.
set -u
TOP="$(git rev-parse --show-toplevel)"
# FAIL-OPEN-ENFORCEMENT (do not remove - asserted by
# scripts/check_guard_exit_consistency.py S1): this runner blocks on exit
# code alone, so a guard printing a FAIL verdict yet exiting 0 would
# false-green the commit. A printed verdict REQUIRES rc 1.
gate_out=$("$TOP/scripts/check_metadata_consistency.py" 2>&1)
gate_rc=$?
printf '%s\n' "$gate_out"
if printf '%s\n' "$gate_out" | grep -qE '(^|[[:space:]])FAIL(ED)?:' && [ "$gate_rc" -ne 1 ]; then
  echo "FAIL: check_metadata_consistency.py printed a FAIL verdict but exited rc $gate_rc (fail-open exit: verdict/exit-code desync), blocking commit"
  exit 1
fi
[ "$gate_rc" -eq 0 ] || exit 1
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
    out=$("$g" --static-only 2>&1)
    rc=$?
    printf '%s\n' "$out"
    # FAIL-OPEN-ENFORCEMENT (do not remove - asserted by
    # scripts/check_guard_exit_consistency.py S1): a printed FAIL verdict
    # REQUIRES rc 1, else the commit false-greens on exit code alone.
    if printf '%s\n' "$out" | grep -qE '(^|[[:space:]])FAIL(ED)?:' && [ "$rc" -ne 1 ]; then
      echo "FAIL: $g printed a FAIL verdict but exited rc $rc (fail-open exit: verdict/exit-code desync), blocking commit"
      exit 1
    fi
    if [ "$rc" -eq 1 ] && ! printf '%s\n' "$out" | grep -qE '(^|[[:space:]])FAIL(ED)?:'; then
      echo "WARN: $g exited 1 with no FAIL verdict line (diagnosability gap) - blocking commit, cause in output above"
    fi
    if [ "$rc" -eq 1 ] || [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
      if [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
        echo "FAIL: $g could not be executed (rc $rc - exec bit or shebang broken), blocking commit"
      fi
      exit 1
    fi
    if [ "$rc" -eq 2 ]; then echo "WARN: $g --static-only infra problem (exit 2), not blocking"; fi
  fi
done
[ "$FOUND" -eq 1 ] || echo "WARN: no --static-only guards discovered under scripts/check_*.py"
exit 0
