#!/usr/bin/env python3
"""Guard: the post-commit hook must correct the guard-run-proof key on amend.

Background (351st review, 2026-11-05): the pre-commit hook records proof
as (HEAD-at-pre-commit-time, staged tree). For a normal commit that key is
the landed commit's (parent, tree); for an AMEND it is (replaced commit,
amended tree), which matches no landed commit, so the amended commit trips
check_hook_run_proof on the NEXT commit. Observed on 074c8cf (the 348th
review's amend of b8828a8): the marker was keyed (b8828a8, amended-tree)
while the landed commit is (8d72657, same tree), and the run had to hand
backfill a marker line. The fix lives in scripts/post-commit-iteration-
log.sh, the one hook that knows the landed commit's real (parent, tree):
after the commit lands it appends a corrected marker keyed on the real
(parent, tree) - but ONLY when the pre-commit hook demonstrably ran for
this tree (the ledger's last line carries this tree, the marker the
pre-commit run appended seconds earlier in the same commit cycle). A
--no-verify commit writes no such marker, so its tree cannot match the
last line unless the tree is unchanged from the last proven commit - in
which case the content was already guard-approved - and the bypass class
stays closed. A normal commit already has a marker for its landed key,
so the correction is a no-op there.

Checks (all static - one small shell read, <2s):
  C1 HARD FAIL: no amend-correction block in the canonical post-commit
     script (marker comment missing).
  C2 HARD FAIL: the correction does not derive the landed parent/tree
     from the landed commit (HEAD^ / HEAD^{tree}).
  C3 HARD FAIL: the correction does not skip when a marker for the
     landed (parent, tree) already exists (normal-commit no-op missing -
     without it every commit would double its ledger lines).
  C4 HARD FAIL: the correction is not gated on the ledger's last line
     carrying the landed tree (the "pre-commit ran this cycle" tie -
     without it a --no-verify commit would get fabricated proof).
  C5 HARD FAIL: the corrected marker is not flagged amend_correction,
     or does not reuse the source marker's guards/hook_sha.
  C6 HARD FAIL: the correction block is not failure-tolerant (not
     wrapped in } 2>/dev/null || true) or the script no longer ends
     with exit 0 - the post-commit hook must never fail a commit.
  C7 HARD FAIL: a parent derivation still uses bare `git rev-parse`
     without --verify: on an unborn branch / root commit it prints the
     literal revision to stdout before failing, so the `|| echo root`
     fallback captures a multi-line parent and the marker is corrupt
     JSON. Pins --verify in the pre-commit proof_parent line and in
     the post-commit LANDED_PARENT line (the stub pre-commit in the
     fixture uses the same form).

Full mode (no --static-only flag; runs in the drift canary): a live
fixture simulation in ~/workspace/sp500-amend-proof-fixture (removed
after): a stub pre-commit reproducing the real pre-commit's proof write
plus the REAL post-commit script, then (a) a normal commit leaves one
marker and no correction, (b) an amend gains a corrected marker keyed
on the landed (parent, tree) and check_hook_run_proof passes on the
fixture, (c) a --no-verify commit gains no marker for its tree, and
(d) a following normal commit makes check_hook_run_proof fail naming
the bypassed commit (the HEAD-grace expires, so the bypass class is
still closed end to end).

Usage:
  scripts/check_amend_proof_correction.py
  scripts/check_amend_proof_correction.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (script unreadable,
      git missing, fixture unwritable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

History:
  2026-11-05 10:30 - created (351st review). Closes the amend-keying
    defect in the guard-run-proof mechanism (074c8cf needed a hand
    backfill); the fixture simulation also caught the bare-rev-parse
    corrupt-marker class, fixed with --verify in the same review (C7).
"""
import json
import os
import shutil
import subprocess
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
POSTCOMMIT = os.path.join(REPO, "scripts", "post-commit-iteration-log.sh")
PROOF_GUARD = os.path.join(REPO, "scripts", "check_hook_run_proof.py")
FIXTURE = os.path.expanduser("~/workspace/sp500-amend-proof-fixture")

MARKER = "GUARD-RUN PROOF AMEND CORRECTION"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def static_checks():
    if not os.path.isfile(POSTCOMMIT):
        print("INFRA: canonical post-commit script missing: " + POSTCOMMIT)
        return 2
    try:
        src = _read(POSTCOMMIT)
    except OSError as e:
        print("INFRA: cannot read post-commit script: %s" % e)
        return 2
    idx = src.find(MARKER)
    check("C1 amend-correction block present in post-commit script",
          idx >= 0,
          "marker comment %r not found" % MARKER if idx < 0 else "")
    if idx < 0:
        return 1
    block = src[idx:]
    # The grep patterns in the shell source escape their double quotes
    # (\" inside a double-quoted shell string); normalize those so the
    # literal checks below match the code, not the escaping.
    flat = block.replace('\\"', '"')
    check("C2 correction derives landed parent/tree (HEAD^ / HEAD^{tree})",
          "HEAD^" in block and "HEAD^{tree}" in block,
          "landed commit derivation missing" if
          ("HEAD^" not in block or "HEAD^{tree}" not in block) else "")
    check("C3 correction skips when landed key already has a marker",
          '"parent":"$LANDED_PARENT","tree":"$LANDED_TREE"' in flat,
          "existing-marker grep missing" if
          '"parent":"$LANDED_PARENT","tree":"$LANDED_TREE"' not in flat
          else "")
    check("C4 correction gated on last ledger line carrying landed tree",
          'tail -n 1' in block and '"tree":"$LANDED_TREE"' in flat,
          "last-line tree gate missing" if
          ('tail -n 1' not in block or '"tree":"$LANDED_TREE"' not in flat)
          else "")
    check("C5 corrected marker flagged + reuses source guards/hook_sha",
          '"amend_correction":true' in block
          and "SRC_GUARDS" in block and "SRC_HOOK" in block,
          "flag or source-field reuse missing" if
          ('"amend_correction":true' not in block
           or "SRC_GUARDS" not in block or "SRC_HOOK" not in block) else "")
    wrapped = block.count("} 2>/dev/null || true") >= 1
    ends_ok = src.rstrip().endswith("exit 0")
    check("C6 correction failure-tolerant, hook still exits 0",
          wrapped and ends_ok,
          "correction block unwrapped or script does not end with exit 0"
          if not (wrapped and ends_ok) else "")
    # C7: --verify on the parent derivations in both hooks. Bare
    # `git rev-parse HEAD` on an unborn branch prints the literal word
    # HEAD to stdout before failing (same for 'HEAD^' on a root commit),
    # so the `|| echo root` fallback would capture a multi-line parent
    # and write a corrupt marker. --verify fails silently instead.
    precommit = os.path.join(REPO, "scripts", "pre-commit-guards.sh")
    try:
        pre_src = _read(precommit)
    except OSError as e:
        print("INFRA: cannot read pre-commit script: %s" % e)
        return 2
    pre_ok = "git rev-parse --verify HEAD" in pre_src
    post_ok = "git rev-parse --verify 'HEAD^'" in block
    detail = ""
    if not (pre_ok and post_ok):
        detail = ("pre-commit proof_parent --verify missing" if not pre_ok
                  else "post-commit LANDED_PARENT --verify missing")
    check("C7 parent derivations use --verify (no corrupt markers)",
          pre_ok and post_ok, detail)
    return 1 if any(not ok for _, ok in results) else 0


# ---------------------------------------------------------------- full mode

STUB_PRECOMMIT = """#!/bin/sh
# Fixture stub: reproduces ONLY the proof-writing tail of
# scripts/pre-commit-guards.sh (the (HEAD, write-tree) marker). The real
# pre-commit hook cannot run in the fixture (it would run the whole 160+
# guard suite against the fixture); the interface between the hooks is
# the ledger line format, reproduced exactly here.
TOP=$(git rev-parse --show-toplevel 2>/dev/null)
PP=$(git rev-parse --verify HEAD 2>/dev/null || echo root)
PT=$(git write-tree 2>/dev/null) || exit 1
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
printf '{"parent":"%s","tree":"%s","guards":1,"hook_sha":"stub","ts":"%s"}\\n' \\
  "$PP" "$PT" "$TS" >> "$TOP/hidden_files/guard_runs.jsonl"
exit 0
"""


def _git(fixture, *args, extra_env=None):
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["ITERATION_LOG"] = os.path.join(fixture, "iteration-log.md")
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com",
         "-C", fixture] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def _ledger_lines(fixture):
    path = os.path.join(fixture, "hidden_files", "guard_runs.jsonl")
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f.read().splitlines() if l.strip()]


def _proof_guard(fixture):
    p = subprocess.run([sys.executable, PROOF_GUARD, "--repo", fixture],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def full_simulation():
    """Live amend / --no-verify fixture. Returns 0/1/2 like main()."""
    if shutil.which("git") is None:
        print("INFRA: git not on PATH - cannot run fixture simulation")
        return 2
    if not os.path.isfile(POSTCOMMIT):
        print("INFRA: canonical post-commit script missing: " + POSTCOMMIT)
        return 2
    fixture = FIXTURE
    try:
        if os.path.exists(fixture):
            shutil.rmtree(fixture)
        os.makedirs(os.path.join(fixture, "hidden_files"))
        rc, out = _git(fixture, "init", "-q")
        if rc != 0:
            print("INFRA: git init failed in fixture: %s" % out)
            return 2
        hooks = os.path.join(fixture, ".git", "hooks")
        shutil.copy(POSTCOMMIT, os.path.join(hooks, "post-commit"))
        with open(os.path.join(hooks, "pre-commit"), "w") as f:
            f.write(STUB_PRECOMMIT)
        os.chmod(os.path.join(hooks, "post-commit"), 0o755)
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)

        def commit_file(text, *args):
            with open(os.path.join(fixture, "a.txt"), "w") as f:
                f.write(text)
            rc, out = _git(fixture, "add", "a.txt")
            assert rc == 0, "git add failed: %s" % out
            rc, out = _git(fixture, "commit", "-q", *args)
            assert rc == 0, "git commit %s failed: %s" % (args, out)
            rc, tree = _git(fixture, "rev-parse", "HEAD^{tree}")
            assert rc == 0, "rev-parse tree failed"
            return tree.strip()

        # (a) normal commit: one marker, no correction line.
        t1 = commit_file("v1\n", "-m", "c1")
        lines = _ledger_lines(fixture)
        check("F1a normal commit: exactly one marker, no correction",
              len(lines) == 1 and lines[0]["parent"] == "root"
              and lines[0]["tree"] == t1
              and "amend_correction" not in lines[0],
              "%d line(s), expected 1 (root, t1)" % len(lines))

        # (a2) second normal commit: two markers, still no correction.
        # The epoch commit (c1) must stay in history: amending the epoch
        # itself is a history rewrite, which check_hook_run_proof
        # correctly fails closed on (its remediation is ledger deletion
        # + re-seed), so the amend under test targets c2, not c1.
        t2 = commit_file("v2\n", "-m", "c2")
        lines = _ledger_lines(fixture)
        check("F1a2 second commit: two markers, no correction",
              len(lines) == 2
              and not any("amend_correction" in m for m in lines),
              "%d line(s), expected 2 with no correction" % len(lines))

        # (b) amend c2: corrected marker keyed on the landed (parent,
        # tree) - c2's parent is c1, so the landed key is (c1, t3).
        rc, c1_sha = _git(fixture, "rev-parse", "HEAD~1")
        assert rc == 0, "rev-parse HEAD~1 failed"
        c1_sha = c1_sha.strip()
        t3 = commit_file("v3\n", "--amend", "-m", "c2 amended")
        lines = _ledger_lines(fixture)
        corrected = [m for m in lines
                     if m.get("amend_correction") is True
                     and m["parent"] == c1_sha and m["tree"] == t3]
        check("F1b amend: corrected marker (c1, amended tree) appended",
              len(corrected) == 1,
              "%d corrected marker(s) for the amended tree" % len(corrected))
        rc, out = _proof_guard(fixture)
        check("F1b proof guard passes on the amended history",
              rc == 0, "check_hook_run_proof rc=%d: %s" % (rc, out.strip()[-200:]))

        # (c) --no-verify commit: no marker for its tree is fabricated.
        t4 = commit_file("v4\n", "--no-verify", "-m", "c3 bypass")
        lines = _ledger_lines(fixture)
        fabricated = [m for m in lines if m["tree"] == t4]
        check("F1c --no-verify commit gains no marker for its tree",
              len(fabricated) == 0,
              "%d marker(s) carry the bypass tree" % len(fabricated))

        # (d) one more normal commit: the bypassed commit is no longer
        # HEAD, so the proof guard must now fail naming it (HEAD-grace
        # expired) - the bypass class stays closed end to end.
        commit_file("v5\n", "-m", "c4")
        rc, out = _proof_guard(fixture)
        check("F1d proof guard fails naming the bypassed commit",
              rc == 1 and "c3 bypass" in out,
              "rc=%d, output names bypass: %s"
              % (rc, "c3 bypass" in out))
    except AssertionError as e:
        print("FAIL: fixture simulation assertion: %s" % e)
        return 1
    except (OSError, subprocess.SubprocessError) as e:
        print("INFRA: fixture simulation error: %s" % e)
        return 2
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
    return 1 if any(not ok for _, ok in results) else 0


def main():
    static_only = "--static-only" in sys.argv
    rc = static_checks()
    if rc == 2:
        return 2
    if rc != 0:
        return 1
    if static_only:
        return 0
    return full_simulation()


if __name__ == "__main__":
    sys.exit(main())
