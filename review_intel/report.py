"""Turns labelled reviews into the comparison page: where each app's negative reviews concentrate, by journey."""
import csv, html, json
from collections import Counter, defaultdict
from .taxonomy import APPS, JOURNEYS, ISSUES, sentiment_from_score


def build(rows, labels, gold=None, run_info=None):
    apps = list(APPS.values())
    per = {a: [r for r in rows if r["app"] == a] for a in apps}
    out = {"apps": {}, "journey_gap": [], "run": run_info or {}}
    neg_share = {}
    for a, rs in per.items():
        if not rs:
            continue
        neg = [r for r in rs if sentiment_from_score(r["score"]) == "negative"]
        jc = Counter(labels[r["rid"]]["journey"] for r in neg)
        ic = defaultdict(Counter)
        for r in neg:
            ic[labels[r["rid"]]["journey"]][labels[r["rid"]]["issue"]] += 1
        neg_share[a] = {j: jc[j] / max(len(neg), 1) for j in JOURNEYS}
        dates = sorted(r["date"] for r in rs)
        out["apps"][a] = {
            "reviews": len(rs), "from": dates[0], "to": dates[-1],
            "negative_pct": round(100 * len(neg) / len(rs), 1),
            "avg_stars": round(sum(int(r["score"]) for r in rs) / len(rs), 2),
            "llm_labelled_pct": round(100 * sum(labels[r["rid"]]["method"] == "llm" for r in rs) / len(rs), 1),
            "negative_by_journey": [{"journey": j, "share_pct": round(100 * jc[j] / max(len(neg), 1), 1), "count": jc[j],
                                     "top_issue": ic[j].most_common(1)[0][0] if ic[j] else None}
                                    for j, _ in jc.most_common()],
            "quotes": {j: [r["text"][:180] for r in sorted((r for r in neg if labels[r["rid"]]["journey"] == j),
                                                           key=lambda r: -int(r["thumbs"]))[:2]]
                       for j, _ in jc.most_common(3)},
        }
    focus, peers = "Angel One", [a for a in apps if a != "Angel One" and a in neg_share]
    if focus in neg_share and peers:
        for j in JOURNEYS:
            peer = sum(neg_share[p][j] for p in peers) / len(peers)
            out["journey_gap"].append({"journey": j, "angel_one_pct": round(100 * neg_share[focus][j], 1),
                                       "peer_avg_pct": round(100 * peer, 1), "gap_pp": round(100 * (neg_share[focus][j] - peer), 1)})
        out["journey_gap"].sort(key=lambda x: -x["gap_pp"])
    if gold:
        def acc(method):
            ok = n = 0
            for g in gold:
                l = labels.get(g["rid"])
                if l and (method == "any" or l["method"] == method):
                    n += 1; ok += l["journey"] == g["journey"]
            return {"n": n, "journey_accuracy_pct": round(100 * ok / n, 1) if n else None}
        from .taxonomy import keyword_label
        kw_ok = sum(keyword_label(g["text"])[0] == g["journey"] for g in gold)
        out["eval"] = {"gold_reviews": len(gold), "llm": acc("llm"),
                       "keyword_baseline": {"n": len(gold), "journey_accuracy_pct": round(100 * kw_ok / len(gold), 1)}}
    return out


def page(summary):
    s = summary
    def bar(pct, color="#1f4e8c"):
        return f"<span style='display:inline-block;height:10px;width:{max(pct,0)*2:.0f}px;background:{color};margin-right:6px'></span>{pct}%"
    rows = "".join(f"<tr><td>{a}</td><td>{d['reviews']}</td><td>{d['from']} to {d['to']}</td><td>{d['avg_stars']}</td><td>{d['negative_pct']}%</td><td>{d['llm_labelled_pct']}%</td></tr>"
                   for a, d in s["apps"].items())
    gap = "".join(f"<tr><td>{JOURNEYS[g['journey']]}</td><td>{bar(g['angel_one_pct'])}</td><td>{bar(g['peer_avg_pct'],'#9aa5b1')}</td><td><b>{g['gap_pp']:+}</b></td></tr>"
                  for g in s["journey_gap"])
    blocks = ""
    for a, d in s["apps"].items():
        items = "".join(f"<li>{JOURNEYS[x['journey']]}: <b>{x['share_pct']}%</b> of negative reviews (top issue: {ISSUES.get(x['top_issue'],'n/a')})</li>" for x in d["negative_by_journey"][:4])
        qs = "".join(f"<li><i>&ldquo;{html.escape(q)}&rdquo;</i> <small>({JOURNEYS[j]})</small></li>" for j, ql in d["quotes"].items() for q in ql[:1])
        blocks += f"<h3>{a}</h3><ul>{items}</ul><p><small>Most-upvoted negative reviews:</small></p><ul>{qs}</ul>"
    ev = s.get("eval")
    evh = (f"<p>Checked against <b>{ev['gold_reviews']}</b> hand-labelled reviews: LLM journey accuracy <b>{ev['llm']['journey_accuracy_pct']}%</b> "
           f"(n={ev['llm']['n']}) vs keyword baseline <b>{ev['keyword_baseline']['journey_accuracy_pct']}%</b>.</p>") if ev else \
          "<p>No hand-labelled check yet: label <code>data/gold_to_label.csv</code> and save it as <code>data/gold.csv</code>.</p>"
    run = s.get("run", {})
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Broking App Review Intel</title><style>body{{font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:auto;padding:16px;color:#1d1d1f;background:#fff}}
table{{border-collapse:collapse;width:100%;margin:8px 0 18px}}td,th{{border-bottom:1px solid #ddd;padding:6px;text-align:left}}small{{color:#555}}</style></head><body>
<h1>Where Indian broking apps lose their users</h1>
<p>Public Play Store reviews (English, India, newest first) for Angel One, Zerodha Kite, Groww and Upstox, labelled by <b>user journey</b> and
<b>issue</b> with an LLM (keyword fallback), refreshed weekly on GitHub Actions. Last run: <b>{run.get('date','')}</b>.</p>
<table><tr><th>App</th><th>Reviews</th><th>Period</th><th>Avg stars</th><th>Negative (1-2 stars)</th><th>LLM-labelled</th></tr>{rows}</table>
<h2>Angel One vs peers: share of negative reviews by journey</h2>
<p><small>Positive gap = this journey makes up a bigger share of Angel One's complaints than the average of the other three apps.</small></p>
<table><tr><th>Journey</th><th>Angel One</th><th>Peer average</th><th>Gap (pp)</th></tr>{gap}</table>
<h2>Per app</h2>{blocks}<h2>How good are the labels?</h2>{evh}
<p><small>Limits: reviews are a self-selected, complaint-heavy sample; English only; the newest reviews per app cover different time spans.
No reviewer names are stored. Code: <a href="https://github.com/f20220970-debug/broking-app-review-intel">broking-app-review-intel</a>.</small></p></body></html>"""
