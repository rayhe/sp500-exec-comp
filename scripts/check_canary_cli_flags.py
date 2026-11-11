#!/usr/bin/env python3
"""Guard: drift_canary.py --help / unknown flags never launch a run.

Background (426th review, 2026-11-11): the canary's hand-rolled argv
loop silently ignored any flag it did not recognize, so a bare
`--help` -- or a typoed flag, a bare positional, `--state` with no
value, or `--shard` with a missing COUNT -- fell through and the run
proceeded as a full ~15-minute canary. The 425th review started one
by accident (`python3 scripts/drift_canary.py --help`) and killed it
at ~3 min; no state was written, but the hazard was real: any operator
typo launches the full suite. The fix rewrites the loop as an
index-based parser: -h/--help prints the docstring Usage block and
exits 0 with no run; unknown flags, bare positionals, and value-taking
flags given no value (or a dash-leading value) exit 2 with usage and
no run. --check-stale and the shard refusal paths are untouched.

Checks:
  S1 HARD FAIL: no -h/--help branch that prints usage and returns 0
     before the guard loop.
  S2 HARD FAIL: no unknown-flag rejection (exit 2 naming the flag).
  S3 HARD FAIL: no missing-value rejection for --state/--log-dir
     (PATH value) or --shard (INDEX COUNT).
  S4 HARD FAIL: the printed usage does not document --help.
  S5 HARD FAIL: the no-arg full-run path is gone (discover/run loop
     after parsing) or the --check-stale short-circuit is gone.
  S6 HARD FAIL: print_usage does not derive from the docstring Usage
     block (printed help could drift from the documented flags).
Behavior (subprocess, 8s ceiling each -- a run that starts is killed
and counted as FAIL; on fixed code every probe returns in <1s):
  R1  --help exits 0, prints Usage, starts no guard run.
  R2  -h behaves like --help.
  R3  --bogus-flag exits 2, names the flag, starts no run.
  R4  --shard 1 (missing COUNT) exits 2, starts no run.
  R5  --state (missing PATH) exits 2, starts no run.
  R6  --state <scratch> --log-dir <scratch> --help exits 0 and writes
      no state file and no per-run log.
  R7  bare positional exits 2, starts no run.
  R8  --log-dir (missing PATH) exits 2, starts no run.
  R9  --check-stale still works hermetically: fresh scratch state
      exits 0 (FRESH), stale scratch state exits 1 (STALE).
  R10 regression: --shard 1 4 --state <missing> still exits 2 naming
      the prior-state refusal, and --shard 5 4 still exits 2 naming
      the out-of-range refusal (check_canary_sharding S3 contract).

Usage:
  scripts/check_canary_cli_flags.py
  scripts/check_canary_cli_flags.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (canary unreadable,
python missing).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
CANARY = os.path.join(REPO, "scripts", "drift_canary.py")

PROBE_TIMEOUT = 8  # seconds; a launched run is still going at this point

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    try:
        src = open(CANARY, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read scripts/drift_canary.py: %s" % exc)
        return 2

    # S1: -h/--help prints usage and returns 0 before any guard runs.
    help_branch = ('in ("-h", "--help")' in src
                   and "print_usage(sys.stdout)" in src
                   and "return 0" in src)
    check("S1 -h/--help branch prints usage and returns 0", help_branch)

    # S2: unknown flags are rejected naming the flag, exit 2.
    s2 = ("unknown flag" in src and "return 2" in src
          and "a.startswith(\"-\")" in src)
    check("S2 unknown dash-flag rejected with exit 2", s2)

    # S3: missing values are rejected, not silently ignored.
    s3a = ("needs a PATH value" in src and "i + 1 >= len(argv)" in src)
    s3b = ("--shard needs integer INDEX COUNT" in src
           and "i + 2 >= len(argv)" in src)
    check("S3a --state/--log-dir missing PATH rejected", s3a)
    check("S3b --shard missing COUNT rejected", s3b)

    # S4: the documented usage lists --help.
    s4 = ("--help" in src and "print this usage, run nothing" in src)
    check("S4 usage documents --help", s4)

    # S5: the no-arg full-run path and the --check-stale short-circuit
    # are intact (the fix must not have removed the real work).
    s5 = ("guards = all_guards" in src
          and "if check_stale_only:" in src
          and "run_guard(name, script, timeout)" in src)
    check("S5 full-run path and --check-stale short-circuit intact", s5)

    # S6: print_usage derives from the docstring Usage block.
    s6 = ("def print_usage" in src
          and 'doc.find("Usage:' in src
          and 'doc.find("\\n\\nEvery run"' in src)
    check("S6 print_usage derives from docstring Usage block", s6)

    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


def run_canary(args):
    """Run the canary with args; return (rc, out, started).

    started=True when the process was still running at PROBE_TIMEOUT:
    it launched a guard run instead of exiting early. The child is
    killed on timeout; a full run writes state/log only at completion,
    so an 8s kill leaves no writes behind.
    """
    proc = subprocess.Popen(
        [sys.executable, CANARY] + args,
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True)
    try:
        out, _ = proc.communicate(timeout=PROBE_TIMEOUT)
        return proc.returncode, out, False
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return None, out, True


def no_run_started(out, started):
    return (not started) and ("canary: running" not in out)


def behavior_checks():
    tmp = tempfile.mkdtemp(prefix="canary_cli_flags_")

    # R1: --help exits 0, prints Usage, starts no run.
    rc, out, started = run_canary(["--help"])
    check("R1 --help exits 0 with usage, no run",
          rc == 0 and "Usage:" in out and "--shard 1 4" in out
          and no_run_started(out, started),
          "rc=%s started=%s out=%r" % (rc, started, out[:120]))

    # R2: -h behaves like --help.
    rc, out, started = run_canary(["-h"])
    check("R2 -h exits 0 with usage, no run",
          rc == 0 and "Usage:" in out and no_run_started(out, started),
          "rc=%s started=%s" % (rc, started))

    # R3: unknown flag exits 2, names the flag, starts no run.
    rc, out, started = run_canary(["--bogus-flag"])
    check("R3 --bogus-flag exits 2 naming the flag, no run",
          rc == 2 and "unknown flag '--bogus-flag'" in out
          and no_run_started(out, started),
          "rc=%s started=%s out=%r" % (rc, started, out[:120]))

    # R4: --shard with a missing COUNT exits 2, starts no run.
    rc, out, started = run_canary(["--shard", "1"])
    check("R4 --shard 1 exits 2, no run",
          rc == 2 and "--shard needs integer INDEX COUNT" in out
          and no_run_started(out, started),
          "rc=%s started=%s" % (rc, started))

    # R5: --state with no PATH exits 2, starts no run.
    rc, out, started = run_canary(["--state"])
    check("R5 --state exits 2, no run",
          rc == 2 and "--state needs a PATH value" in out
          and no_run_started(out, started),
          "rc=%s started=%s" % (rc, started))

    # R6: --help with --state/--log-dir writes nothing.
    scratch_state = os.path.join(tmp, "state.json")
    scratch_logdir = os.path.join(tmp, "logs")
    rc, out, started = run_canary(
        ["--state", scratch_state, "--log-dir", scratch_logdir, "--help"])
    wrote_state = os.path.exists(scratch_state)
    wrote_log = (os.path.isdir(scratch_logdir)
                 and any(f.startswith("canary_")
                         for f in os.listdir(scratch_logdir)))
    check("R6 --help with --state/--log-dir writes nothing",
          rc == 0 and not wrote_state and not wrote_log
          and no_run_started(out, started),
          "rc=%s state=%s log=%s started=%s"
          % (rc, wrote_state, wrote_log, started))

    # R7: bare positional exits 2, starts no run.
    rc, out, started = run_canary(["frobnicate"])
    check("R7 bare positional exits 2, no run",
          rc == 2 and "unexpected argument 'frobnicate'" in out
          and no_run_started(out, started),
          "rc=%s started=%s" % (rc, started))

    # R8: --log-dir with no PATH exits 2, starts no run.
    rc, out, started = run_canary(["--log-dir"])
    check("R8 --log-dir exits 2, no run",
          rc == 2 and "--log-dir needs a PATH value" in out
          and no_run_started(out, started),
          "rc=%s started=%s" % (rc, started))

    # R9: --check-stale still works, hermetically.
    now = datetime.datetime.now(datetime.timezone.utc)
    fresh = os.path.join(tmp, "fresh.json")
    stale = os.path.join(tmp, "stale.json")
    with open(fresh, "w") as f:
        json.dump({"last_run_utc": (now - datetime.timedelta(hours=1))
                   .isoformat(timespec="seconds")}, f)
    with open(stale, "w") as f:
        json.dump({"last_run_utc": (now - datetime.timedelta(hours=100))
                   .isoformat(timespec="seconds")}, f)
    rc_f, out_f, started_f = run_canary(
        ["--check-stale", "--state", fresh])
    rc_s, out_s, started_s = run_canary(
        ["--check-stale", "--state", stale])
    check("R9 --check-stale fresh->0 FRESH, stale->1 STALE",
          rc_f == 0 and "FRESH" in out_f
          and rc_s == 1 and "STALE" in out_s
          and not (started_f or started_s),
          "fresh rc=%s stale rc=%s" % (rc_f, rc_s))

    # R10: the shard refusal paths still exit 2 before any run
    # (check_canary_sharding S3 contract). The out-of-range probe
    # needs a state carrying guard verdicts: shard mode checks for
    # them before partition_guards raises, so a bare last_run_utc
    # fixture would refuse on "no guard verdicts" instead.
    rc, out, started = run_canary(
        ["--shard", "1", "4", "--state", os.path.join(tmp, "missing.json")])
    r10a = (rc == 2 and "prior canary state" in out
            and no_run_started(out, started))
    r10a_rc = rc
    with_verdicts = os.path.join(tmp, "with_verdicts.json")
    with open(with_verdicts, "w") as f:
        json.dump({"last_run_utc": (now - datetime.timedelta(hours=1))
                   .isoformat(timespec="seconds"),
                   "guards": {"check_x": {"status": "pass", "exit": 0,
                                          "seconds": 0.1,
                                          "run_utc": (now - datetime.timedelta(hours=1)).isoformat(timespec="seconds")}},
                   "overall": "pass",
                   "coverage": {"recorded": 1, "discovered": 1,
                                "fresh": 1, "complete": True}}, f)
    rc, out, started = run_canary(
        ["--shard", "5", "4", "--state", with_verdicts])
    r10b = (rc == 2 and "out of range" in out
            and no_run_started(out, started))
    check("R10 shard refusals still exit 2 before any run",
          r10a and r10b,
          "no-state rc=%s out-of-range rc=%s" % (r10a_rc, rc))

    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    rc = behavior_checks()
    failed = [r for r in results if not r[1]]
    if failed or rc:
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
