import csv, json
from pathlib import Path
from review_intel import fetch, classify, report
from review_intel.taxonomy import keyword_label, APPS

RAW = {
 "com.msf.angelmobile": [("Video KYC failed three times, account still not activated after 5 days", 1, 9),
                         ("Withdrawal not credited to bank even after 3 days", 1, 4), ("Great app, easy to trade", 5, 0),
                         ("App crashes at 9:15 when market opens, cannot place order", 1, 7)],
 "com.zerodha.kite3": [("Charts are excellent, smooth order placement", 5, 2), ("Login OTP not coming", 2, 1)],
 "com.nextbillion.groww": [("Hidden charges deducted on every trade", 1, 3), ("Simple and clean", 5, 0)],
 "in.upstox.app": [("Customer care never responds to my ticket", 1, 5), ("Option chain is confusing", 2, 1)],
}
def fake_fetcher(app_id, n):
    return [{"reviewId": f"{app_id}-{i}", "userName": "Real Person", "content": t, "score": s, "thumbsUpCount": th,
             "at": "2026-11-01 10:00:00", "reviewCreatedVersion": "1.0"} for i, (t, s, th) in enumerate(RAW[app_id])]

def test_fetch_drops_names_and_dedupes(tmp_path):
    rows = fetch.fetch_all(10, fetcher=fake_fetcher)
    assert all("userName" not in r and len(r["rid"]) == 16 for r in rows)
    all_rows, added = fetch.merge(tmp_path / "r.csv", rows)
    _, added2 = fetch.merge(tmp_path / "r.csv", rows)
    assert added == len(rows) == 10 and added2 == 0

def test_keyword_baseline():
    assert keyword_label("Video KYC failed, account not activated")[0] == "onboarding_kyc"
    assert keyword_label("Withdrawal not credited to bank")[0] == "funds"
    assert keyword_label("Hidden charges deducted")[0:2] == ("charges_pricing", "unexpected_charges")

def test_parse_rejects_invalid_labels():
    ids = {"a", "b", "c"}
    txt = "```json\n" + json.dumps([{"rid": "a", "journey": "funds", "issue": "delay"},
                                     {"rid": "b", "journey": "made_up", "issue": "delay"},
                                     {"rid": "zzz", "journey": "funds", "issue": "delay"}]) + "\n```"
    assert classify.parse(txt, ids) == {"a": ("funds", "delay")}
    assert classify.parse("not json", ids) == {}

def test_classify_uses_llm_falls_back_and_caches(tmp_path):
    rows = fetch.fetch_all(10, fetcher=fake_fetcher)
    calls = []
    def llm(prompt):
        calls.append(1)
        recs = [json.loads(l) for l in prompt.split("Reviews:\n")[1].splitlines()]
        # label all but the first review, which must fall back to keywords
        return json.dumps([{"rid": r["rid"], "journey": "general", "issue": "other"} for r in recs[1:]])
    labels, info = classify.classify(rows, tmp_path / "l.csv", llm=llm, batch=20)
    methods = [labels[r["rid"]]["method"] for r in rows]
    assert methods.count("keyword") == 1 and methods.count("llm") == 9 and info["llm_requests"] == 1
    classify.classify(rows, tmp_path / "l.csv", llm=llm, batch=20)      # only the keyword-labelled one is retried
    assert len(calls) == 2

def test_classify_survives_llm_errors(tmp_path):
    rows = fetch.fetch_all(10, fetcher=fake_fetcher)
    def broken(prompt): raise RuntimeError("429 quota")
    labels, info = classify.classify(rows, tmp_path / "l.csv", llm=broken)
    assert all(l["method"] == "keyword" for l in labels.values()) and info["llm_errors"]

def test_report_gap_and_eval(tmp_path):
    rows = fetch.fetch_all(10, fetcher=fake_fetcher)
    labels, _ = classify.classify(rows, tmp_path / "l.csv", llm=None)
    gold = [{"rid": r["rid"], "text": r["text"], "journey": labels[r["rid"]]["journey"]} for r in rows]
    s = report.build(rows, labels, gold, {"date": "2026-11-11"})
    ao = s["apps"]["Angel One"]
    assert ao["reviews"] == 4 and ao["negative_pct"] == 75.0
    kyc = next(g for g in s["journey_gap"] if g["journey"] == "onboarding_kyc")
    assert kyc["angel_one_pct"] > 0 and kyc["peer_avg_pct"] == 0
    assert s["eval"]["keyword_baseline"]["journey_accuracy_pct"] == 100.0
    html = report.page(s)
    assert "Real Person" not in html and "Angel One vs peers" in html


def test_prompt_version_bump_relabels(tmp_path):
    rows = fetch.fetch_all(10, fetcher=fake_fetcher)
    lab = lambda p: json.dumps([{"rid": json.loads(l)["rid"], "journey": "general", "issue": "other"} for l in p.split("Reviews:\n")[1].splitlines()])
    classify.classify(rows, tmp_path / "l.csv", llm=lab)
    old = classify.PROMPT_VERSION
    try:
        classify.PROMPT_VERSION = "99"; calls = []
        classify.classify(rows, tmp_path / "l.csv", llm=lambda p: (calls.append(1), lab(p))[1])
        assert calls, "labels from an older prompt must be redone"
    finally:
        classify.PROMPT_VERSION = old
