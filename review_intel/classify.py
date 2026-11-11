"""LLM classification of reviews into journey x issue, with a keyword fallback.

Batches of 20 reviews per request; the model must return JSON with labels from the fixed taxonomy. Anything
invalid or missing falls back to the keyword baseline for that review, and the `method` column records which one
labelled it. Labels are cached in data/labels.csv, so each review is classified once (free-tier daily quotas)."""
import csv, json, os, re, time, urllib.request, urllib.error

PROMPT_VERSION = "2"   # bump when the prompt changes: older LLM labels are redone
from pathlib import Path
from .taxonomy import JOURNEYS, ISSUES, keyword_label

PROMPT = """You label app-store reviews of an Indian stock-broking app.
For each review return its user journey and main issue, using ONLY these ids.
journeys: {journeys}
issues: {issues}
Rules: charts, watchlists, option chain, market depth, order placement and positions are orders_trading.
discovery_research is ONLY recommendations, research reports, screeners, stock ideas, advisory and news.
Pick the journey the complaint or praise is about (e.g. 'money not credited after withdrawal' -> funds;
'video KYC keeps failing' -> onboarding_kyc; 'app freezes at 9:15' -> orders_trading if it blocks trading, else
app_performance). Use 'general' only when no journey applies. Reviews may be in Hinglish.
Return a JSON list: [{{"rid": "...", "journey": "...", "issue": "..."}}] and nothing else.
Reviews:
{reviews}"""


class Gemini:
    def __init__(self, key=None, model=None, pause=None):
        self.key = key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.pause = float(pause if pause is not None else os.environ.get("LLM_PAUSE_SECONDS", "5"))

    def __call__(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                           "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}).encode()
        for attempt in range(4):
            req = urllib.request.Request(url, body, {"Content-Type": "application/json", "x-goog-api-key": self.key})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.load(r)
                time.sleep(self.pause)
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and attempt < 3:
                    time.sleep(20 * (attempt + 1)); continue
                raise


def parse(text, batch_ids):
    """Valid labels only, keyed by rid. Tolerates code fences."""
    text = re.sub(r"^```(json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return {}
    out = {}
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and it.get("rid") in batch_ids and it.get("journey") in JOURNEYS and it.get("issue") in ISSUES:
            out[it["rid"]] = (it["journey"], it["issue"])
    return out


def classify(rows, cache_path: Path, llm=None, batch=20, max_requests=400):
    cache = {r["rid"]: r for r in csv.DictReader(open(cache_path))} if cache_path.exists() else {}
    todo = [r for r in rows if r["rid"] not in cache or cache[r["rid"]]["method"] == "keyword"
            or cache[r["rid"]].get("v", "1") != PROMPT_VERSION]
    errors, requests = [], 0
    if llm is not None:
        for i in range(0, len(todo), batch):
            if requests >= max_requests:
                break
            chunk = todo[i:i + batch]
            ids = {r["rid"] for r in chunk}
            prompt = PROMPT.format(journeys=", ".join(JOURNEYS), issues=", ".join(ISSUES),
                                   reviews="\n".join(json.dumps({"rid": r["rid"], "stars": r["score"], "text": r["text"][:600]}, ensure_ascii=False) for r in chunk))
            try:
                got = parse(llm(prompt), ids); requests += 1
            except Exception as e:  # keep going; these reviews fall back to keywords
                errors.append(str(e)[:120]); got = {}
            for r in chunk:
                if r["rid"] in got:
                    cache[r["rid"]] = {"rid": r["rid"], "journey": got[r["rid"]][0], "issue": got[r["rid"]][1], "method": "llm", "v": PROMPT_VERSION}
    for r in rows:
        if r["rid"] not in cache:
            j, i = keyword_label(r["text"])
            cache[r["rid"]] = {"rid": r["rid"], "journey": j, "issue": i, "method": "keyword", "v": PROMPT_VERSION}
    with open(cache_path, "w", newline="") as f:
        w = csv.DictWriter(f, ["rid", "journey", "issue", "method", "v"], restval="1"); w.writeheader(); w.writerows(cache.values())
    return cache, {"llm_requests": requests, "llm_errors": errors[:5]}
