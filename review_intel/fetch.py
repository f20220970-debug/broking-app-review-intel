"""Fetch the newest public Play Store reviews (English, India) for each app. Runs on GitHub Actions.
Stores no reviewer names: review ids are hashed and only text, rating, date, app version and helpful-votes are kept."""
import csv, hashlib, os
from pathlib import Path
from .taxonomy import APPS

FIELDS = ["rid", "app_id", "app", "score", "date", "app_version", "thumbs", "text"]


def _rid(app_id, review_id):
    return hashlib.sha1(f"{app_id}:{review_id}".encode()).hexdigest()[:16]


def normalise(app_id, raw):
    return {"rid": _rid(app_id, raw["reviewId"]), "app_id": app_id, "app": APPS[app_id], "score": int(raw["score"]),
            "date": str(raw["at"])[:10], "app_version": raw.get("reviewCreatedVersion") or "",
            "thumbs": int(raw.get("thumbsUpCount") or 0), "text": " ".join((raw.get("content") or "").split())}


def fetch_all(per_app=800, fetcher=None):
    if fetcher is None:
        from google_play_scraper import reviews, Sort
        fetcher = lambda app_id, n: reviews(app_id, lang="en", country="in", sort=Sort.NEWEST, count=n)[0]
    out = []
    for app_id in APPS:
        out += [normalise(app_id, r) for r in fetcher(app_id, per_app) if (r.get("content") or "").strip()]
    return out


def merge(path: Path, new_rows):
    old = list(csv.DictReader(open(path))) if path.exists() else []
    seen = {r["rid"] for r in old}
    rows = old + [r for r in new_rows if r["rid"] not in seen]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(rows)
    return rows, len(rows) - len(old)
