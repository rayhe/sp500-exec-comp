#!/usr/bin/env python3
"""Regression guard: the shared render-half helpers are the one
implementation every adopted guard uses.

Background (429th review, 2026-11-11): scripts/render_guard_common.py
generalizes two per-guard copies -- the render-half retry-once wrapper
(427th review, check_badge_part_spans.py) and get_d3_bytes() (identical
in 83 guards) -- and fixes the d3-shim-unavailable exit mapping
(render_checks() returned False -> exit 1 drift, although every
adopter's docstring promises exit 2 infra). Adopters this run:
check_badge_part_spans.py, check_quartile_hash_roundtrip.py,
check_sector_chip_scope.py. The other 80 guards keep their local
copies until a later iteration adopts them, one guard per run.

430th review (2026-11-11): check_network_residual_keyboard.py
adopted (slowest render guard, ~98.3s). Its pre-fix defect was worse
than the 429th class: main() ignored render_checks()'s return value,
so a missing d3 shim exited 0 with "ALL 6 CHECKS PASSED" while the
render half never ran. 79 local get_d3_bytes copies remain.

431st review (2026-11-11): check_minimap_toggle.py adopted (slowest
remaining render guard, ~69.9s). Same silent-pass variant as the
430th: pre-fix main() ignored render_checks()'s return value and
exited 0 with "7/7 checks passed" on a missing d3 shim, proved
in-process before the fix. 78 local get_d3_bytes copies remain.

432nd review (2026-11-12): check_compare_bridge_keyboard.py adopted
(slowest remaining render guard, ~54.2s). Same silent-pass variant:
pre-fix main() ignored render_checks()'s return value and exited 0
with "ALL 6 CHECKS PASSED" on a missing d3 shim, proved in-process
before the fix (~/workspace/pre432_proof.py: exit 0, 0 R-checks). The
pre-adoption grep across the remaining guards found the silent-pass
signature in 77 of the 78 unadopted guards; the lone exception is
check_crosstab_keyboard.py, whose main() already maps a False render
return to exit 2. 77 local get_d3_bytes copies remain.

434th review (2026-11-12): check_remaining_chip_sweeps.py adopted
(slowest remaining render guard, ~49.1s in the 2026-11-12 shard
runs). Its pre-fix defect was the 429th-review class, not the
silent-pass variant: main() checked render_checks()'s return value,
but a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the guard's docstring
promises exit 2 (infra) -- proved in-process before the fix
(/tmp/pre434_proof.py: rc=1, "11/11 checks passed" printed, 0
R-checks recorded). 76 local get_d3_bytes copies remain.

435th review (2026-11-12): check_scrollspy_nav.py adopted (slowest
remaining render guard, ~43.9s max in the 2026-11-12 shard runs).
Same silent-pass variant as the 430th-432nd: pre-fix main() ignored
render_checks()'s return value and exited 0 with "OK: scroll-spy
nav guard (static)" on a missing d3 shim, proved in-process before
the fix (~/workspace/pre435_proof.py: rc=0, "checks: 7 pass, 0
fail", 0 R-checks recorded). Count correction: 77 unadopted guards
carried a local get_d3_bytes before this run, not the 76 the 434th
note stated (the 432nd note's own "77 of the 78 unadopted guards"
already put the unadopted count at 78; the 434th adoption took it
to 77). 76 local get_d3_bytes copies remain after this adoption.

436th review (2026-11-12): check_insight_action_labels.py adopted
(slowest remaining render guard, ~40.4s max in the 2026-11-12 shard
runs; re-profiled from the freshest drift_canary_state.json entries
this run, per the 432nd note). Its pre-fix defect was the
429th-review class, not the silent-pass variant: main() checked
render_checks()'s return value, but a missing d3 shim made
render_checks() return False, which main() folded into exit 1
(drift) although the guard's docstring promises exit 2 (infra) --
proved in-process before the fix (~/workspace/pre436_proof.py: rc=1,
"19/19 checks passed" printed, 0 R-checks recorded). 75 files still
match the grep after this adoption (74 unadopted guards + the
contract guard's S1e string literal).

437th review (2026-11-12): check_vol_board_hash_roundtrip.py adopted
(slowest remaining render guard, ~32.5s max in the 2026-11-12 shard
runs; re-profiled from the freshest drift_canary_state.json entries
this run, per the 432nd note). Same 429th-review class as the 436th:
main() checked render_checks()'s return value, but a missing d3 shim
made render_checks() return False, which main() folded into exit 1
(drift) although the docstring promises exit 2 (infra) -- proved
in-process before the fix (~/workspace/pre437_proof.py: rc=1, "13/13
checks passed" printed, 0 R-checks recorded; the 13 static checks
pass, the 8 render checks never run). 74 files still match the grep
after this adoption (73 unadopted guards + the contract guard's S1e
string literal).

438th review (2026-11-12): check_narrative_sentence2_grammar.py adopted
(slowest remaining render guard, ~25.8s in the 2026-11-12
drift_canary_state.json run; re-profiled from the freshest
drift_canary_state.json entries this run, per the 432nd note). Same
429th-review class as the 436th/437th: main() checked render_checks()'s
return value, but a missing d3 shim made render_checks() return False,
which main() folded into exit 1 (drift) although the guard's docstring
promises exit 2 (infra) -- proved in-process before the fix
(~/workspace/pre438_proof.py: rc=1, "5/5 checks passed" printed, 0
R-checks recorded; the 5 static checks pass, the 5 render checks never
run). 73 files still match the grep after this adoption (72 unadopted
guards + the contract guard's S1e string literal).

442nd review (2026-11-12): check_announce_seven_dims.py adopted
(slowest remaining render guard, ~32.7s in the 2026-11-13T02:31:11Z
shard-4 run; re-profiled from the freshest drift_canary_state.json
entries this run, per the 432nd note). Same 429th-review class as the
436th/437th/438th: main() checked render_checks()'s return value, but
a missing d3 shim made render_checks() return False, which main()
folded into exit 1 (drift) although the guard's docstring promises
exit 2 (infra) -- proved in-process before the fix
(~/workspace/pre442_proof.py: rc=1, "3/3 checks passed" printed, 0
R-checks recorded; the 3 static checks pass, the 3 render checks never
run). 72 files still match the grep after this adoption (71 unadopted
guards + the contract guard's S1e string literal).

451st review (2026-11-13): check_sort_aria_sort.py adopted (slowest
remaining render guard, 42.1s fresh shard-1 verdict in this run;
re-profiled from the freshest drift_canary_state.json entries this
run, per the 432nd note). Same 429th-review class as the
436th/437th/438th/442nd: main() checked render_checks()'s return
value, but a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the guard's docstring
promises exit 2 (infra) -- proved in-process before the fix
(~/workspace/pre451_proof.py: rc=1, "5/5 checks passed" printed, 0
R-checks recorded; the 5 static checks pass, the 5 render checks never
run). 71 files still match the grep after this adoption (70 unadopted
guards + the contract guard's S1e string literal).

459th review (2026-11-14): check_pvp_alignment_card.py adopted (slowest
unadopted render guard, 24.1s fresh shard-3 verdict in the
2026-11-14T05:02:05Z canary run; re-profiled from the freshest
drift_canary_state.json entries this run, per the 432nd note). Same
silent-pass variant as the 430th-432nd, in the S4-harness form:
main() ignored render_checks()'s return value, so a render half
returning INFRA exited 0 with "4/4 checks passed" while the render
half never ran -- proved in-process before the fix
(~/workspace/sp500-459/pre459_proof.py: Test A rc=0, "4/4 checks
passed", 0 R-checks; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). The live missing-d3 path called
sys.exit(2) from inside render_checks(), so the live silent pass was
masked -- but the return-value contract was still broken and the S4
harness could not observe the INFRA mapping. 64 files still match the
grep after this adoption (62 unadopted guards + the shared module's
own definition + the contract guard's S1e string literal).

461st review (2026-11-14): check_position_chip_lone_text.py adopted
(slowest unadopted render guard overall and in shard 4, 38.2s fresh
standalone verdict vs 32.7s for the runner-up check_neo_scroll_hint;
state seconds 21.0s vs 19.6s from the 2026-11-14T09:00Z shard-4 run;
re-profiled with the canary's exact shard function, per the 432nd
note). Same 429th-review class as the 436th/437th/438th/442nd/451st/
457th: main() read render_checks()'s return value, but a missing d3
shim made render_checks() return False, which main() folded into exit
1 (drift) although the docstring promises exit 2 (infra) -- proved
in-process before the fix (~/workspace/sp500-461/pre461_proof.py:
Test A-live rc=1, "10/10 checks passed" printed, 0 R-checks; Test A2
rc=0 on the INFRA-stub form, the truthy sentinel folding to success;
Test B UNCATCHED RuntimeError on a simulated transient Chromium
launch stall). 62 files still match the grep after this adoption
(60 unadopted guards + the shared module's own definition + the
contract guard's S1e string literal). Note: the 460th review added no
docstring note here (ADOPTERS line only); this note restores the
per-review log, the 460th adoption itself is recorded in its guard's
docstring and the iteration log.

462nd review (2026-11-14): check_card_interior_keyboard.py adopted
(slowest unadopted render guard in shard 1, 10.9s state seconds from
the 2026-11-14T10:30Z shard-1 run; re-profiled with the canary's exact
shard function, per the 432nd note). Its pre-fix defects were BOTH
429th-review classes: main() ignored render_checks()'s return value,
so a missing d3 shim exited 0 with "ALL 7 CHECKS PASSED" while the
render half never ran (the 460th-review unmasked silent-pass shape),
and the INFRA sentinel itself is truthy, so a render half returning
INFRA would have exited 0 the same way (latent silent pass, S4 form);
a transient render exception raised before any R-check was uncaught
-- proved in-process before the fix (~/workspace/sp500-462/
pre462_proof.py: Test A-live rc=0, "ALL 7 CHECKS PASSED", 0 R-checks;
Test A2 rc=0, "ALL 7 CHECKS PASSED", 0 R-checks; Test B UNCATCHED
RuntimeError on a simulated transient Chromium launch stall). 61
files still match the grep after this adoption (59 unadopted guards +
the shared module's own definition + the contract guard's S1e string
literal).

463rd review (2026-11-14): check_network_legend_keyboard.py adopted
(slowest unadopted render guard in shard 3, 17.4s state seconds from
the 2026-11-14T13:02Z shard-3 run; re-profiled with the canary's exact
shard function, per the 432nd note). Its pre-fix defects were BOTH
429th-review classes: main() ignored render_checks()'s return value,
so a missing d3 shim exited 0 with "ALL 6 CHECKS PASSED" while the
render half never ran (the 460th-review unmasked silent-pass shape),
and the INFRA sentinel itself is truthy, so a render half returning
INFRA would have exited 0 the same way (latent silent pass, S4 form);
a transient render exception raised before any R-check was uncaught
-- proved in-process before the fix (~/workspace/sp500-463/
pre463_proof.py: Test A-live rc=0, "ALL 6 CHECKS PASSED", 0 R-checks;
Test A2 rc=0, "ALL 6 CHECKS PASSED", 0 R-checks; Test B UNCATCHED
RuntimeError on a simulated transient Chromium launch stall). 60
files still match the grep after this adoption (58 unadopted guards +
the shared module's own definition + the contract guard's S1e string
literal).

464th review (2026-11-14): check_residual_clicks_keyboard.py adopted
(slowest unadopted render guard in shard 2, 14.4s state seconds from
the 2026-11-14T22:28Z shard-2 run; re-profiled with the canary's exact
shard function, per the 432nd note). Its pre-fix defects were BOTH
429th-review classes: main() ignored render_checks()'s return value,
so a missing d3 shim exited 0 with "ALL 11 CHECKS PASSED" while the
render half never ran (the 460th-review unmasked silent-pass shape),
and the INFRA sentinel itself is truthy, so a render half returning
INFRA would have exited 0 the same way (latent silent pass, S4 form);
a transient render exception raised before any R-check was uncaught
--- proved in-process before the fix (~/workspace/sp500-464/
pre464_proof.py: Test A-live rc=0, "ALL 11 CHECKS PASSED", 0 R-checks;
Test A2 rc=0, "ALL 11 CHECKS PASSED", 0 R-checks; Test B UNCATCHED
RuntimeError on a simulated transient Chromium launch stall). 59
files still match the grep after this adoption (57 unadopted guards +
the shared module's own definition + the contract guard's S1e string
literal).

465th review (2026-11-14): check_insight_card_keyboard.py adopted
(slowest unadopted render guard in shard 4, 37.2s state seconds from
the 2026-11-14T17:14Z shard-4 run; re-profiled with the canary's exact
shard function, per the 432nd note). Its pre-fix defects were BOTH
429th-review classes: main() ignored render_checks()'s return value,
so a missing d3 shim exited 0 with all 5 static checks passed while
the render half never ran (the 460th-review unmasked silent-pass
shape -- this guard printed no summary line, so the proof's tell is
the INFRA line as the last output line), and the INFRA sentinel itself
is truthy, so a render half returning INFRA would have exited 0 the
same way (latent silent pass, S4 form); a transient render exception
raised before any R-check was uncaught -- proved in-process before
the fix (~/workspace/sp500-465/pre465_proof.py: Test A-live rc=0,
"INFRA: could not obtain d3.min.js shim" last line, 0 R-checks;
Test A2 rc=0, "PASS: S5 ..." last line, 0 R-checks; Test B UNCATCHED
RuntimeError on a simulated transient Chromium launch stall). The
adoption also adds the "ALL N CHECKS PASSED" / "N/N checks passed"
summary lines this guard never printed. 58 files still match the
grep after this adoption (56 unadopted guards + the shared module's
own definition + the contract guard's S1e string literal).

466th review (2026-11-14): check_position_empty_count_label.py adopted
(slowest unadopted render guard in shard 1, 11.2s state seconds from
the 462nd shard-1 run; re-profiled with the canary's exact shard
function, per the 455th note (17) -- the ranking held exactly:
check_quartile_chip_lone_styling at 11.0s state is the runner-up,
and the fresh standalone re-profile held it too, 47.8s vs 29.7s --
both inflated by the Saturday-evening cron-wave load, same family as
the 465th note (53)). Its pre-fix defects were BOTH 429th-review
classes: (#1, no retry wrapper) a transient render exception raised
before any R-check was uncaught -- traceback, exit 1, 0 R-checks, no
FAIL verdict; (#2, exit-1 mismatch, the 461st-review shape) main()
read render_checks()'s return value, but a missing d3 shim returned
False, which main() folded into exit 1 although the docstring
promises exit 2 -- and the INFRA sentinel itself is truthy, so a
render half returning INFRA would have exited 0 the same way (latent
silent pass, S4 form). Proved in-process before the fix
(~/workspace/sp500-466/pre466_proof.py: Test A-live rc=1, "5/5 checks
passed", 0 R-checks, INFRA line present; Test A2 rc=0, "5/5 checks
passed", 0 R-checks; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). The adoption restructures main()
around run_render_with_retry with the INFRA-to-exit-2 mapping (main()
already returned its exit code, so no sys.exit-to-return conversion
was needed -- the S4 harness observes the returned rc either way),
and adds the "ALL N CHECKS PASSED" summary line on the all-pass path.
render_checks() already returned an explicit bool on success, so no
None-on-success fix was needed (458th note (27) checked). 57 files
still match the grep after this adoption (55 unadopted guards + the
shared module's own definition + the contract guard's S1e string
literal).

467th review (2026-11-14): check_keyboard_seg_pilot.py adopted
(slowest unadopted render guard in shard 3 -- the freshest state
ranking (18.3s for check_inline_onclick_keyboard vs 17.9s here, from
the 463rd shard-3 run, canary_20261114_2102_shard3of4.log) pointed at
inline_onclick by 0.4s, but the multi-run history reverses it: seg
pilot was slower in 8 of the last 9 shard-3 runs (medians ~11.6s vs
~9.4s), and two fresh standalone re-profiles this run held the same
way (13.1s vs 10.5s; 10.2s vs 8.4s) -- the 18.3s/17.9s pair is a
single load-inflated sample (both ~2x their medians, same family as
the 466th note's Saturday-evening cron-wave inflation). inline_onclick
is the presumptive next shard-3 adoption). Its pre-fix defects were
BOTH 429th-review classes: (#1, no retry wrapper) a transient render
exception raised before any R-check was uncaught -- traceback, exit 1,
0 R-checks, no FAIL verdict; (#2, silent pass, the 430th-review shape)
main() ignored render_checks()'s return value, so a missing d3 shim
exited 0 with the 7 static checks passed while the render half never
ran -- and the INFRA sentinel itself is truthy, so a render half
returning INFRA would have exited 0 the same way (latent silent pass,
S4 form). Proved in-process before the fix
(~/workspace/sp500-467/pre467_proof.py: Test A-live rc=0, "INFRA:
could not obtain d3.min.js shim" last line, 0 R-checks; Test A2 rc=0,
"PASS: S7 ..." last line, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The adoption
restructures main() around run_render_with_retry with the INFRA-to-exit-2
mapping, and adds the "ALL N CHECKS PASSED" summary line on the
all-pass path. render_checks() already returned an explicit bool on
success, so no None-on-success fix was needed (458th note (27)
checked). 56 files still match the grep after this adoption (54
unadopted guards + the shared module's own definition + the contract
guard's S1e string literal).

468th review (2026-11-14): check_community_chip_combined_label.py
adopted (slowest unadopted render guard in shard 2, 9.9s state seconds
from the 464th shard-2 run, tied with check_keyboard_pilot_extension
at 9.9s -- the fresh standalone re-profile this run broke the tie
exactly: 39.8s vs 25.4s, both inflated by the Saturday-evening
cron-wave load, same family as the 466th note (55); the 13.3s state
runner-up check_board_chip_survival was not adopted: its render half
aborts d3 requests and never fetches the shim, so the INFRA mapping
would be a fake dependency -- the campaign targets guards with a local
get_d3_bytes, and this guard is the slowest such guard in shard 2).
Its pre-fix defects were BOTH 429th-review classes: (#1, no retry
wrapper) a transient render exception raised before any R-check was
uncaught -- traceback, exit 1, 0 R-checks, no FAIL verdict; (#2,
exit-1 mismatch, the 461st-review shape) main() read render_checks()'s
return value, but a missing d3 shim returned False, which main() folded
into exit 1 although the docstring promises exit 2 -- and the INFRA
sentinel itself is truthy, so a render half returning INFRA would have
exited 0 the same way (latent silent pass, S4 form). Proved in-process
before the fix (~/workspace/sp500-468/pre468_proof.py: Test A-live rc=1,
"6/6 checks passed", 0 R-checks; Test A2 rc=0, "6/6 checks passed",
0 R-checks; Test B UNCATCHED RuntimeError on a simulated transient
Chromium launch stall). The adoption restructures main() around
run_render_with_retry with the INFRA-to-exit-2 mapping, and adds the
"ALL N CHECKS PASSED" summary line on the all-pass path.
render_checks() already returned an explicit bool on success, so no
None-on-success fix was needed (458th note (27) checked). 55 files
still match the grep after this adoption (53 unadopted guards + the
shared module's own definition + the contract guard's S1e string
literal).

470th review (2026-11-15): check_tenure_growth_keyboard.py adopted
(slowest unadopted render guard in shard 1 by the freshest state --
49.1s from the 466th shard-1 run, canary_20261115_0238_shard1of4.log
-- but the multi-run history shows both it and the 40.8s runner-up
(check_sector_gov_keyboard) as load-inflated single samples (both
~8-9s in older shard-1 runs, e.g. tenure 8.4s, sector_gov 9.0s /
8.1s / 7.8s); two fresh standalone re-profiles this run held the
same way (9.78s vs 9.04s), so tenure stays first by the queued order
and the narrow re-profile lead, per the 469th note (68) rule that the
evidence base is the multi-run history plus the re-profile, not one
state reading). Its pre-fix defects were BOTH 429th-review classes:
(#1, no retry wrapper) a transient render exception raised before any
R-check was uncaught -- traceback, exit 1, 0 R-checks, no FAIL
verdict; (#2, silent pass, the 430th-review shape) main() ignored
render_checks()'s return value, so a missing d3 shim exited 0 with
"ALL 7 CHECKS PASSED" while the render half never ran -- and the
INFRA sentinel itself is truthy, so a render half returning INFRA
would have exited 0 the same way (latent silent pass, S4 form).
Proved in-process before the fix
(~/workspace/sp500-470/pre470_proof.py: Test A rc=0, "ALL 7 CHECKS
PASSED", 0 R-checks; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). The adoption restructures main()
around run_render_with_retry with the INFRA-to-exit-2 mapping; the
static-only and playwright-missing branches keep the guard's existing
"ALL N CHECKS PASSED" summary format. render_checks() already
returned an explicit bool on success, so no None-on-success fix was
needed (458th note (27) checked). 53 files still match the grep after
this adoption (51 unadopted guards + the shared module's own
definition + the contract guard's S1e string literal).

474th review (2026-11-15): check_quartile_chip_lone_styling.py adopted
(slowest unadopted render guard in shard 1 by the freshest state --
12.0s from the 2026-11-15T10:37:29Z shard-1 run -- and effectively
tied on the re-profile, 9.74s standalone vs ger 10.65s and
sector_gov 9.94s, within load noise, so the pick stands on the queued
order and the multi-run history: the older state sample was 28.7s for
this guard vs 21.3s ger, per the 469th note (68) rule that the
evidence base is the multi-run history plus the re-profile, not one
state reading). Its pre-fix defects were BOTH 429th-review classes:
(#1, no retry wrapper) a transient render exception raised before
any R-check was uncaught -- traceback, exit 1, 0 R-checks, no FAIL
verdict; (#2, exit-1 mismatch) main() checked render_checks()'s
return value, but a missing d3 shim returned False, which main()
folded into exit 1 (drift) although the docstring promises exit 2
(infra) -- and the pass line printed "6/6 checks passed" alongside
rc=1, the misleading shape the 434th/436th/437th/438th/442nd reviews
fixed; and the INFRA sentinel itself is truthy, so a render half
returning INFRA would have exited 0 the same way (latent silent
pass, S4 form). Proved in-process before the fix
(~/workspace/sp500-474/pre474_proof.py: Test A-live code=1, "6/6
checks passed", 0 R-checks; Test A2 code=0, "6/6 checks passed", 0
R-checks; Test B UNCATCHED RuntimeError on a simulated transient
Chromium launch stall). The adoption restructures main() around
run_render_with_retry with the INFRA-to-exit-2 mapping; the
static-only and playwright-missing branches keep the guard's
existing "N/N checks passed" summary format. render_checks() already
returned an explicit bool on success, so no None-on-success fix was
needed (458th note (27) checked). 49 files still match the grep
after this adoption (47 unadopted guards + the shared module's own
definition + the contract guard's S1e string literal).

475th review (2026-11-15): check_roving_keyboard.py adopted
(slowest unadopted render guard in shard 3 by the freshest state --
17.0s from the 2026-11-15T13:11:31Z shard-3 run -- and by the
re-profile, 26.5s standalone, ahead of crosstab 16.8s and anomaly
14.3s, so the lead holds on both readings, per the 469th note (68)
rule that the evidence base is the multi-run history plus the
re-profile, not one state reading). Its pre-fix defects were BOTH
429th-review classes: (#1, no retry wrapper) a transient render
exception raised before any R-check was uncaught -- traceback, exit
1, 0 R-checks, no FAIL verdict; (#2, silent pass, the 430th-review
shape) main() ignored render_checks()'s return value, so a missing
d3 shim exited 0 with "ALL 6 CHECKS PASSED" while the render half
never ran -- and the INFRA sentinel itself is truthy, so a render
half returning INFRA would have exited 0 the same way (latent silent
pass, S4 form). Proved in-process before the fix
(~/workspace/sp500-475/pre475_proof.py: Test A-live code=0, "ALL 6
CHECKS PASSED", 0 R-checks; Test A2 code=0, "ALL 6 CHECKS PASSED", 0
R-checks; Test B UNCATCHED RuntimeError on a simulated transient
Chromium launch stall). The adoption restructures main() around
run_render_with_retry with the INFRA-to-exit-2 mapping; the
static-only and playwright-missing branches keep the guard's
existing "ALL N CHECKS PASSED" summary format. render_checks()
already returned an explicit bool on success, so no None-on-success
fix was needed (458th note (27) checked). 48 files still match the
grep after this adoption (46 unadopted guards + the shared module's
own definition + the contract guard's S1e string literal).

478th review (2026-11-15): check_ger_keyboard.py adopted (slowest
adoptable shard-1 render guard by the multi-run history plus the
re-profile: 13.3s fresh in-shard (477th state) and 83.91s standalone
(this run; load-inflated vs 10.65s standalone at the 474th) vs yoy
11.7s fresh in-shard and 30.51s standalone this run -- ger leads
both readings, per the 469th note (68) rule that the evidence base
is the multi-run history plus the re-profile, not one state
reading). Its pre-fix defects were BOTH 429th-review classes:
(#1, no retry wrapper) a transient render exception raised before
any R-check was uncaught -- traceback, exit 1, 0 R-checks, no FAIL
verdict; (#2, silent pass, the 430th-review shape) main() ignored
render_checks()'s return value (only the None/SKIP branch was
checked), so a missing d3 shim exited 0 with "ALL 8 CHECKS PASSED"
while the render half never ran -- and the INFRA sentinel itself is
truthy, so a render half returning INFRA would have exited 0 the
same way (latent silent pass, S4 form). Proved in-process before
the fix (~/workspace/sp500-478/pre478_proof.py: Test A-live code=0,
0 R-checks; Test A2 code=0, 0 R-checks; Test B UNCATCHED
RuntimeError on a simulated transient Chromium launch stall). The
adoption restructures main() around run_render_with_retry with the
INFRA-to-exit-2 mapping; the adopted main() gains the uniform
"ALL N CHECKS PASSED" summary line, replacing the pre-fix
"ALL n CHECKS PASSED" / SKIP-fall-through shape.
render_checks() already returned an explicit bool on success, so no
None-on-success fix was needed (458th note (27) checked). 44
check_*.py files still match the source-only grep after this
adoption (43 unadopted guards + the contract guard's S1e string
literal, which occurs twice in that file, so 45 matching lines);
the recursive scripts/ grep adds the shared module's own definition
(46 lines over 45 .py files) plus one stale __pycache__ .pyc (the
472nd note (76) trap -- quote the source-only count going forward).

477th review (2026-11-15): check_detail_peer_nav_keyboard.py adopted
(slowest adoptable shard-3 render guard by the multi-run history
plus the re-profile: 15.6s / 15.4s / 35.2s in-shard (0502 / 1307 /
2102 shard-3 runs) and 32.31s standalone (this run) vs crosstab
13.7s / 16.9s / 34.2s and 28.29s standalone, pathfinder 11.5s /
16.1s / 30.2s and 26.21s standalone, inline-onclick 11.1s / 11.5s /
31.2s and 21.66s standalone -- detail-peer-nav leads all four
readings, per the 469th note (68) rule that the evidence base is the
multi-run history plus the re-profile, not one state reading).
Its pre-fix defects were BOTH 429th-review classes: (#1, no retry
wrapper) a transient render exception raised before any R-check was
uncaught -- traceback, exit 1, 0 R-checks, no FAIL verdict; (#2,
silent pass, the 430th-review shape) main() ignored
render_checks()'s return value entirely, so a missing d3 shim
exited 0 with "TOTAL: 4/4 passed" while the render half never ran --
and the INFRA sentinel itself is truthy, so a render half returning
INFRA would have exited 0 the same way (latent silent pass, S4
form). Proved in-process before the fix
(~/workspace/sp500-477/pre477_proof.py: Test A-live code=0, 0
R-checks; Test A2 code=0, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The adoption
restructures main() around run_render_with_retry with the
INFRA-to-exit-2 mapping; the adopted main() gains the uniform
"ALL N CHECKS PASSED" summary line, replacing the pre-fix
"TOTAL: n/n passed" / "STATIC-ONLY: n/n passed" lines.
render_checks() already returned an explicit bool on success, so no
None-on-success fix was needed (458th note (27) checked). 45
check_*.py files still match the source-only grep after this
adoption (44 unadopted guards + the contract guard's S1e string
literal, which occurs twice in that file, so 46 matching lines);
the recursive scripts/ grep adds the shared module's own definition
(47 lines over 46 .py files) plus one stale __pycache__ .pyc (the
472nd note (76) trap -- quote the source-only count going forward).

476th review (2026-11-15): check_keyboard_pilot_extension.py adopted
(slowest adoptable shard-2 render guard by the multi-run history
plus the re-profile: 12.37s standalone (472nd) and 8.64s standalone
(this run) vs pctile 10.72s / 7.48s; in-shard 9.9s (468th) and 12.0s
(472nd) vs pctile 7.9s / 12.5s -- keyboard leads 3 of 5 readings,
both clean standalone re-profiles, and carries the worse defect
class, per the 469th note (68) rule that the evidence base is the
multi-run history plus the re-profile, not one state reading).
Board re-profiled slowest overall (12.39s standalone this run;
26.4s / 15.0s in-shard) but is NOT adoptable under the current
contract: it carries no local fetcher (its render half aborts all d3
requests and never needs the shim), so there is no honest INFRA
return site for it -- a shim fetch there would be a false INFRA
probe; a retry-only adoption would need a contract extension. Its
pre-fix defects were BOTH 429th-review classes: (#1, no retry
wrapper) a transient render exception raised before any R-check was
uncaught -- traceback, exit 1, 0 R-checks, no FAIL verdict; (#2,
silent pass, the 430th-review shape) main() decided on the results
list alone (render_checks()'s return value checked only for None),
so a missing d3 shim exited 0 with no R-checks recorded while the
render half never ran -- and the INFRA sentinel itself is truthy, so
a render half returning INFRA would have exited 0 the same way
(latent silent pass, S4 form). Proved in-process before the fix
(~/workspace/sp500-476/pre476_proof.py: Test A-live code=0, 0
R-checks; Test A2 code=0, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The adoption
restructures main() around run_render_with_retry with the
INFRA-to-exit-2 mapping; the guard printed no summary line pre-fix,
so the adopted main() gains the uniform "ALL N CHECKS PASSED"
summary format rather than preserving one. render_checks() already
returned an explicit bool on success, so no None-on-success fix was
needed (458th note (27) checked). 46 check_*.py files still match
the source-only grep after this adoption (45 unadopted guards + the
contract guard's S1e string literal, which occurs twice in that file,
so 47 matching lines); the recursive scripts/ grep adds the shared
module's own definition (48 lines over 47 .py files) plus one stale
__pycache__ .pyc (the 472nd note (76) trap -- quote the source-only
count going forward).

473rd review (2026-11-15): check_neo_scroll_hint.py adopted
(slowest unadopted render guard in shard 4 by the freshest state --
20.5s from the 2026-11-15T09:09:58Z shard-4 run,
canary_20261115_0909_shard4of4.log -- and by the re-profile, 23.15s
standalone, ahead of combined_chip_sector_prefix 16.57s and
network_edge_overlay 16.91s; the older shard-4 runs showed 32.6-33.5s
for this guard, so the lead holds across the multi-run history, per
the 469th note (68) rule that the evidence base is the multi-run
history plus the re-profile, not one state reading). Its pre-fix
defects were BOTH 429th-review classes: (#1, no retry wrapper) a
transient render exception raised before any R-check was uncaught --
traceback, exit 1, 0 R-checks, no FAIL verdict; (#2, silent pass, the
430th-review shape) main() ignored render_checks()'s return value, so
a missing d3 shim exited 0 with "6/6 checks passed" while the render
half never ran -- and the INFRA sentinel itself is truthy, so a render
half returning INFRA would have exited 0 the same way (latent silent
pass, S4 form). Proved in-process before the fix
(~/workspace/sp500-473/pre473_proof.py: Test A-live code=0, "6/6 checks
passed", 0 R-checks; Test A2 code=0, "6/6 checks passed", 0 R-checks;
Test B UNCATCHED RuntimeError on a simulated transient Chromium launch
stall). The adoption restructures main() around run_render_with_retry
with the INFRA-to-exit-2 mapping; the static-only and
playwright-missing branches keep the guard's existing
"N/N checks passed" summary format. render_checks() already returned
an explicit bool on success, so no None-on-success fix was needed
(458th note (27) checked). 50 files still match the grep after this
adoption (48 unadopted guards + the shared module's own definition +
the contract guard's S1e string literal).

472nd review (2026-11-15): check_ratio_chip_combined_label.py adopted
(slowest unadopted render guard in shard 2 by the freshest state --
32.6s from the 468th shard-2 run, canary_20261115_0645_shard2of4.log
-- the 470th note flagged the 32.6s figure as load-inflated against
an 8.2s earlier state sample, so this run re-profiled the top three
shard-2 candidates standalone: ratio 14.98s,
keyboard_pilot_extension 12.37s, pctile 10.72s -- ratio stays first by
the queued order and the re-profile lead, per the 469th note (68)
rule that the evidence base is the multi-run history plus the
re-profile, not one state reading). Its pre-fix defects were BOTH
429th-review classes: (#1, no retry wrapper) a transient render
exception raised before any R-check was uncaught -- traceback, exit 1,
0 R-checks, no FAIL verdict; (#2, exit-1 mismatch) main() checked
render_checks()'s return value, but a missing d3 shim returned False,
which main() folded into exit 1 (drift) although the docstring
promises exit 2 (infra) -- and the pass line printed "6/6 checks
passed" alongside rc=1, the misleading shape the 434th/436th/437th/
438th/442nd reviews fixed. Proved in-process before the fix
(~/workspace/sp500-472/pre472_proof.py: Test A rc=1, "6/6 checks
passed", 0 R-checks; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). The adoption restructures main()
around run_render_with_retry with the INFRA-to-exit-2 mapping; the
static-only and playwright-missing branches keep the guard's existing
"N/N checks passed" summary format. No None-on-success fix was needed
here (458th note (27) checked): render_checks() already returns
r1_ok and r2_ok and r3_ok explicitly. 51 files still match the grep
after this adoption (49 unadopted guards + the shared module's own
definition + the contract guard's S1e string literal).

471st review (2026-11-15): check_scatter_brush_keyboard.py adopted
(slowest unadopted render guard in shard 3 by the freshest state --
16.9s from the 467th shard-3 run, canary_20261115_0502_shard3of4.log
-- the multi-run history agrees (15.6s, 16.0s, 17.3s, 22.9s across
the last five shard-3 runs; the runner-up
check_detail_peer_nav_keyboard sits at 9.0-15.6s); two fresh
standalone re-profiles this run held the same way (25.89s vs 11.60s),
so scatter_brush stays first by the queued order and the re-profile
lead, per the 469th note (68) rule that the evidence base is the
multi-run history plus the re-profile, not one state reading). Its
pre-fix defects were BOTH 429th-review classes: (#1, no retry
wrapper) a transient render exception raised before any R-check was
uncaught -- traceback, exit 1, 0 R-checks, no FAIL verdict; (#2,
silent pass, the 430th-review shape) main() ignored
render_checks()'s return value, so a missing d3 shim exited 0 with
"ALL 6 CHECKS PASSED" while the render half never ran -- and the
INFRA sentinel itself is truthy, so a render half returning INFRA
would have exited 0 the same way (latent silent pass, S4 form).
Proved in-process before the fix
(~/workspace/sp500-471/pre471_proof.py: Test A rc=0, "ALL 6 CHECKS
PASSED", 0 R-checks; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). The adoption restructures main()
around run_render_with_retry with the INFRA-to-exit-2 mapping; the
static-only and playwright-missing branches keep the guard's existing
"ALL N CHECKS PASSED" summary format. A None-on-success fix was
needed here (458th note (27) checked): render_checks() returned None
implicitly on success, so it now returns all(ok ...) after the last
R-check. 52 files still match the grep after this adoption (50
unadopted guards + the shared module's own definition + the contract
guard's S1e string literal).

469th review (2026-11-15): check_network_keyboard.py adopted
(slowest unadopted render guard in shard 4 -- the freshest state
ranking (38.2s for check_zero_row_single_dim_badge vs 37.3s here,
from the 465th shard-4 run, canary_20261115_0113_shard4of4.log)
pointed at zero_row by 0.9s, but the multi-run history reverses it:
network keyboard was slower in 8 of the last 10 shard-4 runs
(medians 17.8s vs 14.2s), and two fresh standalone re-profiles this
run held the same way (15.6s vs 11.7s; 14.6s vs 12.9s) -- the
38.2s/37.3s pair is a single load-inflated sample (both ~2-3x their
medians, same family as the 466th note's Saturday-evening cron-wave
inflation, per the 467th precedent). check_zero_row_single_dim_badge
is the presumptive next shard-4 adoption). Its pre-fix defects were
BOTH 429th-review classes: (#1, no retry wrapper) a transient render
exception raised before any R-check was uncaught -- traceback, exit
1, 0 R-checks, no FAIL verdict; (#2, silent pass, the 430th-review
shape) main() ignored render_checks()'s return value, so a missing
d3 shim exited 0 with the 9 static checks passed while the render
half never ran -- and the INFRA sentinel itself is truthy, so a
render half returning INFRA would have exited 0 the same way (latent
silent pass, S4 form). Proved in-process before the fix
(~/workspace/sp500-469/pre469_proof.py: Test A-live rc=0, "INFRA:
could not obtain d3.min.js shim" last line, 0 R-checks; Test A2 rc=0,
"PASS: S9 ..." last line, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The adoption
restructures main() around run_render_with_retry with the
INFRA-to-exit-2 mapping, and adds the "ALL N CHECKS PASSED" summary
line on the all-pass path (this guard printed no summary line
before). render_checks() already returned an explicit bool on
success, so no None-on-success fix was needed (458th note (27)
checked). 54 files still match the grep after this adoption (52
unadopted guards + the shared module's own definition + the contract
guard's S1e string literal).

Checks (all pure Python, no browser; <2s):
  S1  the shared module defines INFRA, get_d3_bytes and
      run_render_with_retry; each adopted guard imports all three
      from render_guard_common, defines no local get_d3_bytes (and
      the badge guard no local _render_with_retry), calls
      run_render_with_retry(render_checks, results, check) in main,
      and maps INFRA to exit 2.
  S2  harness for run_render_with_retry: raise-once-then-True returns
      True after 2 calls with no FAIL recorded; raise-twice returns
      False with exactly one synthetic FAIL recorded; raise-after-an-
      R-check returns False after 1 call with no synthetic FAIL;
      an INFRA return passes through after 1 call; a None return
      passes through after 1 call.
  S3  get_d3_bytes(): the real cache returns >= 100KB; a missing
      cache + a failing curl returns None (curl stubbed in-process,
      no network).
  S4  each adopted guard maps INFRA to exit 2 with no FAIL verdict
      line: the guard module is imported in-process, its
      render_checks is stubbed to return INFRA, main() returns 2.

Usage:
  scripts/check_render_guard_common.py
  scripts/check_render_guard_common.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (shared module or
an adopted guard unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import contextlib
import importlib.util
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_guard_common as rgc  # noqa: E402

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
SCRIPTS = os.path.join(REPO, "scripts")
COMMON = os.path.join(SCRIPTS, "render_guard_common.py")

ADOPTERS = [
    "check_badge_part_spans.py",
    "check_quartile_hash_roundtrip.py",
    "check_sector_chip_scope.py",
    "check_network_residual_keyboard.py",
    "check_minimap_toggle.py",
    "check_compare_bridge_keyboard.py",
    "check_remaining_chip_sweeps.py",
    "check_scrollspy_nav.py",
    "check_insight_action_labels.py",
    "check_vol_board_hash_roundtrip.py",
    "check_narrative_sentence2_grammar.py",
    "check_announce_seven_dims.py",
    "check_sort_aria_sort.py",
    "check_quartile_position_sector_prefix.py",
    "check_scroll_hint.py",
    "check_stockpct_chip_combined_label.py",
    "check_position_hash_roundtrip.py",
    "check_kbd_hint_header.py",
    "check_community_hash_roundtrip.py",
    "check_radar_label_keyboard.py",
    "check_pvp_alignment_card.py",
    "check_methodology_buttons.py",
    "check_position_chip_lone_text.py",
    "check_card_interior_keyboard.py",
    "check_network_legend_keyboard.py",
    "check_residual_clicks_keyboard.py",
    "check_insight_card_keyboard.py",
    "check_position_empty_count_label.py",
    "check_keyboard_seg_pilot.py",
    "check_community_chip_combined_label.py",
    "check_network_keyboard.py",
    "check_tenure_growth_keyboard.py",
    "check_scatter_brush_keyboard.py",
    "check_ratio_chip_combined_label.py",
    "check_neo_scroll_hint.py",
    "check_quartile_chip_lone_styling.py",
    "check_roving_keyboard.py",
    "check_keyboard_pilot_extension.py",
    "check_detail_peer_nav_keyboard.py",
    "check_ger_keyboard.py",
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def s1_adoption_static():
    try:
        src = open(COMMON, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read render_guard_common.py: %s" % exc)
        return None
    ok = "INFRA = object()" in src
    check("S1a shared module defines the INFRA sentinel", ok,
          "" if ok else "INFRA sentinel missing from render_guard_common.py")
    ok = "def get_d3_bytes(" in src
    check("S1b shared module defines get_d3_bytes", ok,
          "" if ok else "get_d3_bytes missing from render_guard_common.py")
    ok = "def run_render_with_retry(" in src
    check("S1c shared module defines run_render_with_retry", ok,
          "" if ok else "run_render_with_retry missing from render_guard_common.py")
    for name in ADOPTERS:
        path = os.path.join(SCRIPTS, name)
        try:
            gsrc = open(path, encoding="utf-8").read()
        except OSError as exc:
            print("INFRA: cannot read %s: %s" % (name, exc))
            return None
        short = name[:-3]
        ok = ("from render_guard_common import INFRA, get_d3_bytes, "
              "run_render_with_retry" in gsrc)
        check("S1d %s imports INFRA/get_d3_bytes/run_render_with_retry"
              % short, ok,
              "" if ok else "%s does not import the shared helpers" % name)
        ok = "def get_d3_bytes(" not in gsrc
        check("S1e %s defines no local get_d3_bytes" % short, ok,
              "" if ok else "%s still carries a local get_d3_bytes" % name)
        ok = "run_render_with_retry(render_checks, results, check)" in gsrc
        check("S1f %s calls run_render_with_retry in main" % short, ok,
              "" if ok else "%s main() does not use the shared retry" % name)
        ok = "if ok is INFRA:" in gsrc
        check("S1g %s maps INFRA to exit 2 in main" % short, ok,
              "" if ok else "%s main() has no INFRA branch" % name)
        ok = "return INFRA" in gsrc
        check("S1h %s returns INFRA when the d3 shim is unavailable" % short, ok,
              "" if ok else "%s render_checks() never returns INFRA" % name)
        if name == "check_badge_part_spans.py":
            ok = "def _render_with_retry(" not in gsrc
            check("S1i badge guard defines no local _render_with_retry", ok,
                  "" if ok else "badge guard still carries a local _render_with_retry")
    return all(r[1] for r in results if r[0].startswith("S1"))


def s2_retry_harness():
    calls = {"n": 0}
    recorded = []

    def record_fail(name, ok, detail=""):
        recorded.append((name, bool(ok), detail))

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("stall")
        return True

    out = rgc.run_render_with_retry(flaky, [], record_fail)
    check("S2a raise-once-then-True returns True after 2 calls, no FAIL",
          out is True and calls["n"] == 2 and recorded == [],
          "out=%r calls=%d recorded=%r" % (out, calls["n"], recorded))

    recorded.clear()
    calls["n"] = 0

    def always_raise():
        calls["n"] += 1
        raise RuntimeError("boom")

    out = rgc.run_render_with_retry(always_raise, [], record_fail)
    synth = [r for r in recorded
             if r[0] == "R1 render half raised on both attempts" and not r[1]]
    check("S2b raise-twice returns False with exactly one synthetic FAIL",
          out is False and len(synth) == 1 and len(recorded) == 1,
          "out=%r recorded=%r" % (out, recorded))

    recorded.clear()
    calls["n"] = 0
    prior = [("R1 something", False, "pre-recorded")]

    def late_raise():
        calls["n"] += 1
        raise RuntimeError("boom")

    out = rgc.run_render_with_retry(late_raise, prior, record_fail)
    check("S2c raise-after-an-R-check returns False after 1 call, no retry",
          out is False and calls["n"] == 1 and prior == [("R1 something", False, "pre-recorded")]
          and recorded == [],
          "out=%r calls=%d prior=%r recorded=%r" % (out, calls["n"], prior, recorded))

    calls["n"] = 0

    def returns_infra():
        calls["n"] += 1
        return rgc.INFRA

    out = rgc.run_render_with_retry(returns_infra, [], record_fail)
    check("S2d INFRA return passes through after 1 call (no retry)",
          out is rgc.INFRA and calls["n"] == 1,
          "out=%r calls=%d" % (out, calls["n"]))
    calls["n"] = 0

    def returns_none():
        calls["n"] += 1
        return None

    out = rgc.run_render_with_retry(returns_none, [], record_fail)
    check("S2e None return (playwright missing) passes through after 1 call",
          out is None and calls["n"] == 1,
          "out=%r calls=%d" % (out, calls["n"]))
    return all(r[1] for r in results if r[0].startswith("S2"))


def s3_d3_bytes():
    try:
        data = rgc.get_d3_bytes()
    except Exception as exc:  # noqa: BLE001 - cache read failure is a guard input
        check("S3a cached d3 shim returns >= 100KB", False, "%s: %s" % (type(exc).__name__, exc))
        data = None
    else:
        check("S3a cached d3 shim returns >= 100KB",
              isinstance(data, (bytes, bytearray)) and len(data) >= 100000,
              "got %r" % (len(data) if isinstance(data, (bytes, bytearray)) else data,))
    from unittest import mock

    class _Stub:
        returncode = 1

    with mock.patch.object(rgc.subprocess, "run", return_value=_Stub()):
        got = rgc.get_d3_bytes(cache="/nonexistent/sp500-d3-shim.js")
    check("S3b missing cache + failing curl returns None (no network)",
          got is None, "got %r" % (got,))
    return all(r[1] for r in results if r[0].startswith("S3"))


def s4_infra_exit_mapping():
    for name in ADOPTERS:
        short = name[:-3]
        path = os.path.join(SCRIPTS, name)
        spec = importlib.util.spec_from_file_location("sp500_" + short, path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:  # noqa: BLE001 - import failure is a guard input
            check("S4 %s imports for the INFRA harness" % short, False,
                  "%s: %s" % (type(exc).__name__, exc))
            continue
        if not hasattr(mod, "INFRA"):
            check("S4 %s imports INFRA (adoption missing)" % short, False,
                  "%s has no INFRA name" % name)
            continue
        mod.render_checks = lambda: mod.INFRA
        old_argv = sys.argv
        sys.argv = [name]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = mod.main()
        finally:
            sys.argv = old_argv
        out = buf.getvalue()
        check("S4 %s maps a d3-shim INFRA to exit 2, no FAIL verdict" % short,
              rc == 2 and "FAIL:" not in out,
              "rc=%s output tail=%r" % (rc, out.strip().splitlines()[-3:]))
    return all(r[1] for r in results if r[0].startswith("S4"))


def main():
    # Pure-Python guard: identical checks in both modes. The literal
    # "--static-only" in sys.argv below is the hook-discovery opt-in
    # (421st review: the docstring mention alone does not opt in).
    _static_only = "--static-only" in sys.argv
    s1 = s1_adoption_static()
    if s1 is None:
        return 2
    s2 = s2_retry_harness()
    s3 = s3_d3_bytes()
    s4 = s4_infra_exit_mapping()
    failed = [r for r in results if not r[1]]
    print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
