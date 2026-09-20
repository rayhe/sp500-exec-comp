#!/usr/bin/env python3
"""2026-09-20 02:00 PT: resolve the 2 missing say-on-pay values (BX, KKR).

Finding (primary-source, this run): neither company holds a say-on-pay vote.
- BX (Blackstone Inc.), 2026 10-K (acc 0001193125-26-082531, filed 2026-02-27):
  "we will generally not be subject to the 'say-on-pay' and 'say-on-frequency'
  provisions of the Dodd-Frank Act. As a result, our common stockholders do not
  have an opportunity to provide a non-binding vote on the compensation of our
  named executive officers." Controlled company; zero DEF 14A filings ever under
  CIK 0001393818 (verified via efts + full submissions history).
- KKR (KKR & Co. Inc.), 2026 10-K (acc 0001404912-26-000007, filed 2026-02-27):
  "We are neither required to conduct say-on-pay or say-on-frequency votes nor
  to provide disclosures relating to pay-versus-performance under the
  Dodd-Frank Act until after the Sunset Date."

So the "498/500" was not a collection gap: 500/500 resolved = 498 advisory
votes + 2 structural exemptions. Records use the exempt taxonomy (no
approval_pct, so _sopApproval stays null and all UI guards behave).

Also: metadata last_updated -> 2026-09-20; PvP metadata gains a rollout
exclusion note (KKR/BX exempt from 402(v); KKR only until Sunset Date).
"""
import json, copy

P = "data/compensation.json"
d = json.load(open(P))
cos = {c["ticker"]: c for c in d["companies"]}

SOP = {
    "BX": {
        "exempt": True,
        "exemption_basis": "Controlled company; Dodd-Frank controlled-company exemption from say-on-pay and say-on-frequency",
        "note": "Per 2026 10-K: \"we will generally not be subject to the 'say-on-pay' and 'say-on-frequency' provisions of the Dodd-Frank Act. As a result, our common stockholders do not have an opportunity to provide a non-binding vote on the compensation of our named executive officers.\" No advisory vote held; no DEF 14A ever filed under CIK 0001393818.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1393818/000119312526082531/d48618d10k.htm",
        "filing_date": "2026-02-27",
    },
    "KKR": {
        "exempt": True,
        "exemption_basis": "Controlled company; exempt from say-on-pay, say-on-frequency, and Item 402(v) pay-versus-performance disclosure until the Sunset Date",
        "note": "Per 2026 10-K: \"We are neither required to conduct say-on-pay or say-on-frequency votes nor to provide disclosures relating to pay-versus-performance under the Dodd-Frank Act until after the Sunset Date.\" No advisory vote held.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1404912/000140491226000007/kkr-20251231.htm",
        "filing_date": "2026-02-27",
    },
}

for t, rec in SOP.items():
    assert cos[t].get("say_on_pay") in (None,), t
    cos[t]["say_on_pay"] = copy.deepcopy(rec)
    print("set", t)

d["last_updated"] = "2026-09-20"
json.dump(d, open(P, "w"), indent=1)
print("last_updated -> 2026-09-20")

PP = "data/pay_vs_performance.json"
p = json.load(open(PP))
p["metadata"]["rollout_exclusions"] = (
    "KKR & Co. Inc. (KKR): exempt from Item 402(v) pay-versus-performance "
    "disclosure until its Sunset Date per 2026 10-K (acc 0001404912-26-000007); "
    "exclude from 402(v) rollout until then. Blackstone Inc. (BX): controlled "
    "company, generally not subject to Dodd-Frank say-on-pay/say-on-frequency "
    "provisions per 2026 10-K (acc 0001193125-26-082531); treat 402(v) as "
    "exempt likewise."
)
json.dump(p, open(PP, "w"), indent=1)
print("pvp rollout_exclusions noted")
