#!/bin/sh
# post-commit hook: append an iteration-log stub for every commit.
#
# Installed 2026-09-12 to kill the recurring commit-without-log-entry pattern
# (f79fe6b, 19696aa, b9137a2, ee84409, 4e78c2e and earlier): every commit in this
# checkout now leaves a timestamped stub in the canonical iteration log, which the
# next scheduled run backfills with detail (replacing the [AUTO-STUB] header).
#
# Install:  cp scripts/post-commit-iteration-log.sh .git/hooks/post-commit && chmod +x .git/hooks/post-commit
# Test:     ITERATION_LOG=/tmp/test-log.md git commit ...   (override, never writes the real log in tests)
#
# The hook NEVER fails a commit: all work is wrapped and it always exits 0.

LOG="${ITERATION_LOG:-$HOME/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/iteration-log.md}"
{
    HASH=$(git rev-parse HEAD 2>/dev/null)
    SUBJ=$(git log -1 --format=%s 2>/dev/null | tr -d '\n')
    if [ -n "$HASH" ] && [ -f "$LOG" ] && ! grep -q "$HASH" "$LOG" 2>/dev/null; then
        # Dedupe by commit SUBJECT (2026-09-14): an amend keeps the subject but
        # changes the hash, which used to append a second stub for the same
        # logical commit (observed on 00ab5ca, 6c32d2c). If an iteration-log
        # header already covers this subject (AUTO-STUB or a backfilled entry),
        # the commit is already logged - no new stub. Uses awk index() for an
        # exact-substring match on header lines ("## ...") only, so body text
        # mentioning the subject cannot false-positive.
        SUBJ_LOGGED=$(awk -v s="$SUBJ" '/^## / && index($0, s) { found=1 } END { print (found ? "yes" : "no") }' "$LOG" 2>/dev/null)
        if [ "$SUBJ_LOGGED" != "yes" ]; then
            TS=$(TZ=America/Los_Angeles date '+%Y-%m-%d %H:%M %Z' 2>/dev/null)
            {
                printf '\n## %s - Iteration [AUTO-STUB] (%s)\n\n' "$TS" "$SUBJ"
                printf -- '- Commit: `%s` - auto-appended by the repo post-commit hook (installed 2026-09-12).\n' "$HASH"
                printf -- '- Detail to be backfilled by the next scheduled run; this stub exists so the\n'
                printf -- '  commit-without-log-entry pattern cannot recur silently.\n\n'
            } >> "$LOG"
        fi
    fi
} 2>/dev/null || true
# GUARD-RUN PROOF AMEND CORRECTION (2026-11-05 10:30 - 351st review;
# check_amend_proof_correction.py). The pre-commit hook records proof as
# (HEAD-at-pre-commit-time, staged tree). For a normal commit that key is
# the landed commit's (parent, tree); for an AMEND it is (replaced commit,
# amended tree), which matches no landed commit, so the amended commit
# trips check_hook_run_proof on the NEXT commit (observed on 074c8cf, the
# 348th review's amend, which needed a hand backfill). This hook knows the
# landed commit's real (parent, tree), so it corrects the key here - but
# ONLY when the pre-commit hook demonstrably ran for this tree: the
# ledger's last line must carry this tree (it is the marker the pre-commit
# run appended seconds earlier in this same commit cycle). A --no-verify
# commit writes no such marker, so its tree cannot match the last line
# unless the tree is unchanged from the last proven commit - in which case
# the content was already guard-approved - and the bypass class stays
# closed. A normal commit already has a marker for its landed key, so the
# correction is a no-op there. Like the stub block above, this never fails
# a commit: all work is wrapped and the hook always exits 0.
# --verify (351st review, 2026-11-05): bare `git rev-parse 'HEAD^'` on a
# root commit prints the literal HEAD^ to stdout before failing, so the
# fallback would capture a multi-line parent and write a corrupt marker;
# --verify fails silently instead, so the fallback yields "root".
{
    ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    LEDGER="$ROOT/hidden_files/guard_runs.jsonl"
    if [ -n "$ROOT" ] && [ -f "$LEDGER" ]; then
        LANDED_PARENT=$(git rev-parse --verify 'HEAD^' 2>/dev/null || echo root)
        LANDED_TREE=$(git rev-parse --verify 'HEAD^{tree}' 2>/dev/null)
        if [ -n "$LANDED_TREE" ] \
            && ! grep -q "\"parent\":\"$LANDED_PARENT\",\"tree\":\"$LANDED_TREE\"" "$LEDGER" 2>/dev/null; then
            LAST_LINE=$(tail -n 1 "$LEDGER" 2>/dev/null)
            if printf '%s' "$LAST_LINE" | grep -q "\"tree\":\"$LANDED_TREE\"" 2>/dev/null; then
                SRC_GUARDS=$(printf '%s' "$LAST_LINE" | sed -n 's/.*"guards":\([0-9][0-9]*\).*/\1/p' 2>/dev/null)
                SRC_HOOK=$(printf '%s' "$LAST_LINE" | sed -n 's/.*"hook_sha":"\([0-9a-f]*\)".*/\1/p' 2>/dev/null)
                CORR_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
                printf '{"parent":"%s","tree":"%s","guards":%s,"hook_sha":"%s","ts":"%s","amend_correction":true}\n' \
                    "$LANDED_PARENT" "$LANDED_TREE" "${SRC_GUARDS:-0}" "$SRC_HOOK" "$CORR_TS" >> "$LEDGER"
            fi
        fi
    fi
} 2>/dev/null || true
exit 0
