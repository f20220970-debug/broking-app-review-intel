"""fetch -> classify -> report. `python run.py --no-fetch` reuses data/reviews.csv."""
import argparse, csv, datetime as dt, json, os, sys
from pathlib import Path
from review_intel import fetch, classify, report, gold

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser(); p.add_argument("--no-fetch", action="store_true"); p.add_argument("--per-app", type=int, default=800)
a = p.parse_args()
data = ROOT / "data"; docs = ROOT / "docs"; data.mkdir(exist_ok=True); docs.mkdir(exist_ok=True)
added = 0
if not a.no_fetch:
    rows, added = fetch.merge(data / "reviews.csv", fetch.fetch_all(a.per_app))
else:
    rows = list(csv.DictReader(open(data / "reviews.csv")))
llm = classify.Gemini() if os.environ.get("GEMINI_API_KEY") else None
labels, info = classify.classify(rows, data / "labels.csv", llm=llm)
if not (data / "gold_to_label.csv").exists() and rows:
    gold.sample(rows, data / "gold_to_label.csv")
gold_rows = [g for g in csv.DictReader(open(data / "gold.csv")) if g.get("journey")] if (data / "gold.csv").exists() else None
run = {"date": dt.date.today().isoformat(), "reviews_total": len(rows), "new_reviews": added, **info,
       "llm_used": llm is not None}
s = report.build(rows, labels, gold_rows, run)
json.dump(s, open(docs / "summary.json", "w"), indent=1)
(docs / "index.html").write_text(report.page(s))
print(json.dumps({k: v for k, v in s.items() if k != "apps"}, indent=1))
if llm is not None and info["llm_requests"] == 0:
    sys.exit("LLM key set but no successful LLM call: check GEMINI_API_KEY / GEMINI_MODEL (page shows keyword-only labels)")
