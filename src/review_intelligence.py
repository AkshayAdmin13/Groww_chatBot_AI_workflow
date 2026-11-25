"""
Step 1: Review Intelligence Layer
Analyzes recent customer reviews to identify themes, quotes and fee confusion.
"""
import os
import re
import csv
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEWS_PATH = os.path.join(BASE_DIR, 'data', 'reviews', 'customer_reviews.csv')

# Theme keyword rules — deterministic, explainable clustering (max 5 themes)
THEME_RULES = {
    "Exit load / Redemption charges confusion": [
        "exit load", "exit-load", "charged", "deducted", "redemption", "redeemed",
        "1%", "hidden charge", "stp", "partial withdrawal", "silent", "charge"
    ],
    "Expense ratio / TER transparency": [
        "expense ratio", "ter", "expense", "1.05%", "1.02%", "factsheet", "fee"
    ],
    "ELSS lock-in understanding": [
        "elss", "lock-in", "lock in", "3 years", "tax saver"
    ],
    "Minimum SIP amount clarity": [
        "minimum sip", "sip", "₹100", "rs 100", "500"
    ],
    "UI / Navigation & report access": [
        "statement", "download", "nav", "benchmark", "riskometer", "app", "slow",
        "load", "menu", "notification", "calculator"
    ],
}

FEE_RULES = {
    "exit_load": {
        "keywords": ["exit load", "1%", "within 1 year", "within 12 months", "charged", "deducted", "redemption"],
        "label": "Exit load (1% if redeemed within 1 year)",
        "theme": "Exit load / Redemption charges confusion",
        "source_urls": [
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
        ],
    },
    "expense_ratio": {
        "keywords": ["expense ratio", "ter", "1.02%", "1.05%", "1.07%"],
        "label": "Expense ratio (annual scheme fee)",
        "theme": "Expense ratio / TER transparency",
        "source_urls": [
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
        ],
    },
}


def load_reviews(path=REVIEWS_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _score_review(text, keywords):
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def analyze_reviews(path=REVIEWS_PATH):
    reviews = load_reviews(path)
    theme_scores = defaultdict(list)
    for r in reviews:
        text = r['review_text']
        scores = {name: _score_review(text, kws) for name, kws in THEME_RULES.items()}
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            theme_scores[best].append(r)

    # Map to max 5 themes, sorted by volume
    themes = []
    for name, items in sorted(theme_scores.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        themes.append({
            "theme": name,
            "count": len(items),
            "share_pct": round(100 * len(items) / len(reviews), 1),
            "avg_rating": round(sum(float(i['rating']) for i in items) / len(items), 1),
        })

    top3 = themes[:3]

    # Extract 3 real user quotes (prefer low-rated, fee-related, substantive)
    scored = []
    for r in reviews:
        text = r['review_text']
        sev = _score_review(text, FEE_RULES['exit_load']['keywords'])
        scored.append((sev, -float(r['rating']), len(text), r))
    scored.sort(key=lambda x: (x[0], x[2]), reverse=True)
    quotes = []
    seen = set()
    for sev, neg_rating, length, r in scored:
        if r['review_id'] in seen:
            continue
        if sev == 0 and len(quotes) >= 2:
            break
        quotes.append({
            "review_id": r['review_id'],
            "date": r['date'],
            "rating": int(float(r['rating'])),
            "text": r['review_text'],
        })
        seen.add(r['review_id'])
        if len(quotes) == 3:
            break

    # Detect recurring fee confusion — count matches per fee type
    fee_counts = {}
    for key, rule in FEE_RULES.items():
        cnt = sum(1 for r in reviews if _score_review(r['review_text'], rule['keywords']) > 0)
        fee_counts[key] = cnt
    detected_key = max(fee_counts, key=fee_counts.get)
    detected = FEE_RULES[detected_key]
    fee_issue = {
        "key": detected_key,
        "label": detected['label'],
        "mentions": fee_counts[detected_key],
        "related_theme": detected['theme'],
        "source_urls": detected['source_urls'],
        "example_quotes": [q['text'] for q in quotes if _score_review(q['text'], detected['keywords']) > 0][:2],
    }

    return {
        "generated_at": datetime.now().strftime('%Y-%m-%d'),
        "total_reviews": len(reviews),
        "date_range": f"{min(r['date'] for r in reviews)} to {max(r['date'] for r in reviews)}",
        "themes": themes,
        "top3_themes": top3,
        "quotes": quotes,
        "fee_issue": fee_issue,
    }


if __name__ == '__main__':
    import json
    print(json.dumps(analyze_reviews(), indent=2, ensure_ascii=False))
