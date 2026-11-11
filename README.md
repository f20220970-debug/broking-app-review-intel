# Broking App Review Intel: where Indian trading apps lose their users

[![weekly-review-intel](https://github.com/f20220970-debug/broking-app-review-intel/actions/workflows/weekly.yml/badge.svg)](https://github.com/f20220970-debug/broking-app-review-intel/actions/workflows/weekly.yml)

**Live page:** `https://f20220970-debug.github.io/broking-app-review-intel/` (refreshed every Monday)

Built while applying for **Angel One's Product Intern** role. It pulls the newest public Play Store reviews for **Angel One, Zerodha Kite, Groww and Upstox**, labels each one by **user journey** (account opening & KYC, funds, orders & trading, discovery, portfolio, charges, support, login, app stability) and **issue** (delay, failure, confusing UX, missing feature, crash, unexpected charges, poor support, praise), and compares where each app's complaints concentrate.

## How it works
```
FETCH     google-play-scraper: newest 800 English reviews per app (India); no reviewer names kept, ids hashed
LABEL     Gemini labels 20 reviews per request with ids from a fixed taxonomy; invalid or missing output falls
          back to a keyword classifier, and every label records which method produced it; labels are cached
REPORT    per app: negative share, journeys behind negative reviews, top issue per journey, most-upvoted quotes;
          Angel One vs peer average by journey (gap in percentage points)
CHECK     160 sampled reviews (40 per app) to label by hand -> journey accuracy of the LLM vs the keyword baseline
```
Runs weekly on GitHub Actions and publishes `docs/index.html` and `docs/summary.json`.

## Reading it honestly
- App-store reviews are **self-selected and complaint-heavy**: they show where pain concentrates, not how many users feel it.
- "Newest 800" covers a few days for a big app and weeks for a smaller one; the page shows each app's date range.
- English only, so Hindi-script reviews are missed; Hinglish in Latin script is included.
- Labels are checked against a hand-labelled sample before any number is trusted.

## Setup
1. Repository secret `GEMINI_API_KEY`; variables `GEMINI_MODEL` (e.g. `gemini-3.1-flash-lite`) and `LLM_PAUSE_SECONDS` (e.g. `5`).
2. Settings → Pages → deploy from `main`, `/docs`.
3. Actions → weekly-review-intel → Run workflow.
4. Label `data/gold_to_label.csv` (fill `journey` and `issue` with the ids above), save as `data/gold.csv`, push.

```
pip install -r requirements.txt
pytest -q                       # dedupe, no names stored, taxonomy validation, LLM fallback, caching, report maths
GEMINI_API_KEY=... python run.py
```
