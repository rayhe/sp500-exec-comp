#!/usr/bin/env python3
"""Regression guard: the Pay-vs-Performance coverage_note must name every
roster ticker missing from the PvP panel, on its CURRENT roster ticker.

Background (428th review, 2026-11-11): the PvP panel covers 498 of 518
roster companies; the 20-ticker gap set is documented in the live
exclusion groups (index.html PvP coverage desc, js/app.js PVP_EXCLUSIONS)
and in the coverage_note audit trail - except the note named only 18 of
the 20:
  - SKYD appeared only as PSKY, in the wave-31 exclusion ("EXCLUSION:
    PSKY - no DEF 14A exists on CIK 0002041610, only 2026 proxy-fight
    variants"). The ticker was renamed PSKY -> SKYD on 2026-10-06
    (Skydance Corporation; Class B listing moved Nasdaq -> NYSE) and the
    tracker key was updated 2026-10-25, but the note was never re-tickered.
    The 2026-09-30 normalization set the precedent for renaming tickers
    in this same note (FI->FISV, BF-B->BF-A) so it stays on current
    roster tickers; the PSKY mention was missed in that normalization.
    Re-verified live 2026-11-11: CIK 0002041610 submissions show 0 DEF
    14A ever filed, and the 2026-04-24 10-K/A Part III carries no 402(v)
    table (0 mentions of "pay versus performance" / "compensation
    actually paid"), so the exclusion ground is unchanged - only the
    ticker spelling was stale.
  - VMRK appeared nowhere in the note. Vivmark Residential (AvalonBay
    Communities + Equity Residential merger of equals, closed
    2026-08-17; CIK 906107) has filed no post-merger DEF 14A (latest DEF
    14A on the CIK is the pre-merger EQR 2026 proxy, 2026-04-14,
    accession 0001193125-26-155007); zero-row stub, queued for extraction
    when its first proxy files. Re-verified live 2026-11-11 via EDGAR
    submissions. The note's single "post-merger" mention is about AVB,
    not VMRK, so the deferral was undocumented in the audit trail.
A reader searching the note for SKYD or VMRK found nothing, and the
dead PSKY token was the only trace of the Skydance exclusion. The fix
re-tickers the wave-31 exclusion to SKYD with the rename parenthetical
("(ticker PSKY until the 2026-10-06 rename)") and appends a dated
2026-11-11 normalization clause recording both the re-tickering and the
VMRK deferral. The note carries no em/en dashes (hyphens only), so the
new clause uses hyphens.

Checks (static - local file reads, <1s):
  S1  HARD FAIL: every roster ticker absent from pvp['companies'] is
      named as a whole word in coverage_note (the gap set is fully
      documented in the audit trail). Pre-fix fails naming SKYD, VMRK.
  S2  HARD FAIL: the wave-31 exclusion carries SKYD with the rename
      parenthetical, so the historical alias stays auditable.
  S3  HARD FAIL: "PSKY" occurs exactly once in the note (inside that
      parenthetical) - no other stale-ticker occurrence.
  S4  HARD FAIL: the VMRK deferral clause names CIK 906107 and the
      2026-04-14 pre-merger EQR proxy, so the deferral is
      filing-grounded, not bare.
  S5  HARD FAIL: the latest "Wave N" marker in the note is still 38 -
      the appended normalization clause introduces no new wave marker,
      so the wave-38 pins in check_pvp_method_coverage_sync.py and
      check_readme_pvp_vintage.py keep passing.

Usage:
  scripts/check_pvp_note_gap_sync.py
  scripts/check_pvp_note_gap_sync.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JSON unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import json
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
PVP_JSON = os.path.join(REPO, "data", "pay_vs_performance.json")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    try:
        pvp = json.load(open(PVP_JSON, encoding="utf-8"))
        comp = json.load(open(COMP_JSON, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("INFRA: cannot read PvP/comp JSON: %s" % exc)
        return 2

    note = pvp.get("metadata", {}).get("coverage_note", "")
    roster = set(c["ticker"] for c in comp.get("companies", []))
    shipped = set(pvp.get("companies", {}).keys())
    gap = sorted(roster - shipped)

    # S1: the whole gap set is named in the note (whole-word match, so
    # single-letter tickers like K cannot match inside other words).
    missing = [t for t in gap
               if not re.search(r"\b" + re.escape(t) + r"\b", note)]
    check("S1 every PvP gap ticker is named in coverage_note (%d gap)"
          % len(gap),
          not missing,
          "unnamed gap tickers: %s" % ", ".join(missing) if missing else "")

    # S2: the wave-31 exclusion carries SKYD with the rename parenthetical.
    s2 = re.search(
        r"EXCLUSION: SKYD \(ticker PSKY until the 2026-10-06 rename\)",
        note) is not None
    check("S2 wave-31 exclusion names SKYD with the PSKY rename parenthetical",
          s2,
          "wave-31 exclusion still names PSKY or lacks the parenthetical"
          if not s2 else "")

    # S3: PSKY occurs exactly once (inside that parenthetical).
    n_psky = len(re.findall(r"PSKY", note))
    check("S3 'PSKY' occurs exactly once in the note (the parenthetical)",
          n_psky == 1,
          "%d occurrences" % n_psky if n_psky != 1 else "")

    # S4: the VMRK deferral is filing-grounded (CIK + pre-merger proxy).
    s4 = ("VMRK" in note and "906107" in note
          and "2026-04-14" in note
          and "0001193125-26-155007" in note)
    check("S4 VMRK deferral names CIK 906107 + 2026-04-14 pre-merger proxy",
          s4,
          "VMRK deferral missing or not filing-grounded" if not s4 else "")

    # S5: the appended clause adds no new wave marker (latest stays 38).
    waves = [int(w) for w in re.findall(r"[Ww]ave (\d+)", note or "")]
    latest = max(waves) if waves else None
    check("S5 latest Wave marker in the note is still 38",
          latest == 38,
          "latest wave is %s" % latest if latest != 38 else "")

    return 0


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    failed = [r for r in results if not r[1]]
    print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
