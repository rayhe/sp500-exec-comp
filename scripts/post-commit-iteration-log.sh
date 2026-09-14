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
exit 0
