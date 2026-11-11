#!/usr/bin/env python3
"""Guard: drift-canary per-run log file (shard auditability).

Failure mode (419th/420th reviews): the re-baseline was auditable only
via the hand-saved shard-1 logs -- shards 2-4 ran but left no per-run
trace, so the state file was the only evidence a shard had ever run.
drift_canary.py (421st review) writes its own per-run log
(canary_YYYYMMDD_HHMM_shardNofM.log / canary_YYYYMMDD_HHMM_full.log)
next to the state file, capturing every printed line. Three invariants
must hold, or the audit trail silently stops existing again:

  S1 shard_log_name returns the documented filename shape for shard
     runs and full runs, and distinct runs never collide on a name
     (different shard index / count / mode produce different names).
  S2 write_run_log writes the exact lines (plus a trailing newline),
     creates missing parent directories, returns the written path, and
     returns None -- never raises -- when the target cannot be written
     (a log-write failure must not fail the canary run itself).
  S3 main() wires the log: the source parses --log-dir / --no-log and
     calls write_run_log with the shard_log_name for the run.

All checks are pure-function / source-text (no subprocess, no Chromium,
no guard runs): the static half stays fast, and the live end-to-end
proof is the real shard run in the 421st review's log file.

Usage:
  scripts/check_canary_shard_log.py              # same checks
  scripts/check_canary_shard_log.py --static-only # same checks

Exit: 0 = all checks pass; 1 = a check FAILED (blocks the commit);
      2 = infra problem (missing drift_canary module).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-11-11 02:30 - created (421st review). Pins the per-run log
    file added the same run (queued candidate (2) from the 419th and
    420th reviews: canary auditability).
"""
import datetime
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import drift_canary as dc
except ImportError as e:  # pragma: no cover - import failure is infra
    print("INFRA: cannot import drift_canary (%s)" % e)
    sys.exit(2)

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def main(argv):
    # S1: filename shape, per mode, with no collisions across runs.
    fn = getattr(dc, "shard_log_name", None)
    if fn is None:
        check("canary-shard-log-name", False,
              "drift_canary has no shard_log_name (feature absent)")
    else:
        start = datetime.datetime(2026, 11, 11, 2, 30,
                                  tzinfo=datetime.timezone.utc)
        shard_name = fn(start, (2, 4))
        full_name = fn(start, None)
        ok = bool(re.fullmatch(r"canary_20261111_0230_shard2of4\.log",
                               shard_name))
        ok = ok and bool(re.fullmatch(r"canary_20261111_0230_full\.log",
                                      full_name))
        # Distinct runs must not collide on a name.
        ok = ok and len({fn(start, (i, 4)) for i in range(1, 5)}) == 4
        ok = ok and fn(start, (1, 4)) != fn(start, (1, 2))
        ok = ok and fn(start, (1, 4)) != full_name
        check("canary-shard-log-name", ok,
              "shard=%s full=%s" % (shard_name, full_name))

    # S2: write_run_log writes exact lines, makes parent dirs, fails soft.
    wr = getattr(dc, "write_run_log", None)
    if wr is None:
        check("canary-shard-log-write", False,
              "drift_canary has no write_run_log (feature absent)")
    else:
        s2_ok = True
        s2_detail = ""
        with tempfile.TemporaryDirectory() as tmp:
            nested = os.path.join(tmp, "a", "b")
            lines = ["canary: running check_x ...",
                     "canary: check_x PASS exit=0 0.4s",
                     "canary: overall PASS"]
            path = wr(nested, "canary_20261111_0230_shard1of4.log", lines)
            if path is None or not os.path.isfile(path):
                s2_ok = False
                s2_detail = "no file written under %s" % nested
            else:
                with open(path) as f:
                    body = f.read()
                if body != "\n".join(lines) + "\n":
                    s2_ok = False
                    s2_detail = "log body is not the exact lines"
                elif path != os.path.join(
                        nested, "canary_20261111_0230_shard1of4.log"):
                    s2_ok = False
                    s2_detail = "returned path %s is not the written file" % path
            # Unwritable target: a path that is a file, not a directory.
            blocker = os.path.join(tmp, "blocker")
            with open(blocker, "w") as f:
                f.write("x")
            try:
                bad = wr(blocker, "x.log", ["one"])
            except Exception as e:  # noqa: BLE001 - fail-soft is the point
                s2_ok = False
                s2_detail = "write_run_log raised %r instead of None" % e
            else:
                if bad is not None:
                    s2_ok = False
                    s2_detail = "unwritable target returned %r, not None" % bad
        if s2_ok:
            s2_detail = "exact lines + trailing newline, parents created, unwritable returns None"
        check("canary-shard-log-write", s2_ok, s2_detail)

    # S3: main() wires the log (source-text pins; the live proof is the
    # real shard run, whose log file the 421st review verified).
    src = ""
    try:
        with open(os.path.join(HERE, "drift_canary.py")) as f:
            src = f.read()
    except OSError as e:
        check("canary-shard-log-wiring", False, "cannot read source: %s" % e)
        src = None
    if src is not None:
        main_src = src.split("def main(argv):", 1)[-1]
        ok = ('"--log-dir"' in main_src and '"--no-log"' in main_src
              and "write_run_log(" in main_src
              and "shard_log_name(start_dt, shard)" in main_src
              and "log_lines" in main_src)
        check("canary-shard-log-wiring", ok,
              "--log-dir/--no-log parsed, write_run_log(shard_log_name) "
              "called in main" if ok else
              "main() does not wire the per-run log (flags/call missing)")

    failed = [n for n, ok, _ in results if not ok]
    if failed:
        print("FAIL: %s" % ", ".join(failed))
        return 1
    print("PASS: all %d canary-shard-log checks passed" % len(results))
    return 0


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
