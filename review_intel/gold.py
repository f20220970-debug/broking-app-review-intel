"""Sample reviews for hand-labelling (the honest check on the LLM)."""
import csv, random
from pathlib import Path


def sample(rows, path: Path, per_app=40, seed=7):
    rng = random.Random(seed); out = []
    for app in sorted({r["app"] for r in rows}):
        rs = [r for r in rows if r["app"] == app]
        out += rng.sample(rs, min(per_app, len(rs)))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, ["rid", "app", "score", "text", "journey", "issue"]); w.writeheader()
        w.writerows({"rid": r["rid"], "app": r["app"], "score": r["score"], "text": r["text"], "journey": "", "issue": ""} for r in out)
    return len(out)
