"""
Steps 2 & 3: Weekly Product Pulse + Fee Explainer generation.
Uses Groq LLM when available, with deterministic local fallbacks so the
workflow always produces a valid, grounded output.
"""
import os
from datetime import datetime

import yaml
from dotenv import load_dotenv
from groq import Groq

from review_intelligence import analyze_reviews

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.yaml')
load_dotenv(os.path.join(BASE_DIR, '.env'))


def _config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _client():
    cfg = _config().get('llm', {})
    key = os.getenv(cfg.get('api_key_env', 'GROQ_API_KEY'))
    return Groq(api_key=key) if key else None


PULSE_SYSTEM = """You are a product analyst. Write a concise weekly product pulse for an internal product team.
Rules: <=250 words; use only the provided data; neutral tone; no investment advice; include exact quotes."""

FEE_SYSTEM = """You are a customer support content writer. Write a clear, neutral, facts-only explanation of a mutual fund fee.
Rules: exactly 6 short bullet points; no advice; no performance claims; cite only the provided official source links."""


def _llm_call(client, system, user, max_tokens=400):
    cfg = _config().get('llm', {})
    resp = client.chat.completions.create(
        model=cfg.get('model', 'qwen/qwen3.8-27b'),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=cfg.get('temperature', 0.0),
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def generate_weekly_pulse(insights, client=None):
    client = client if client is not None else _client()
    top = insights['top3_themes']
    quotes = insights['quotes']
    fee = insights['fee_issue']
    if client:
        try:
            user = f"""Data: {insights['total_reviews']} reviews ({insights['date_range']}).
Top themes: {[(t['theme'], t['count']) for t in top]}.
Quotes: {[q['text'] for q in quotes]}.
Fee confusion: {fee['label']} ({fee['mentions']} mentions).
Write the weekly pulse with: Summary of top themes, Supporting user quotes, Key observation, 3 action ideas."""
            return _llm_call(client, PULSE_SYSTEM, user, max_tokens=350)
        except Exception:
            pass

    # Deterministic fallback
    lines = [
        f"# Weekly Product Pulse — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"**Scope:** {insights['total_reviews']} public reviews ({insights['date_range']}).",
        "",
        "## Top Themes",
    ]
    for i, t in enumerate(top, 1):
        lines.append(f"{i}. **{t['theme']}** — {t['count']} mentions ({t['share_pct']}%), avg rating {t['avg_rating']}/5")
    lines += ["", "## What Users Are Saying"]
    for q in quotes:
        lines.append(f"- “{q['text']}” — review {q['review_id']}, {q['date']} (rating {q['rating']}/5)")
    lines += [
        "",
        "## Key Observation",
        f"{fee['label']} is the single most recurring confusion ({fee['mentions']} mentions). Users describe the charge as unexpected or unclear at the time of redemption, especially near the 1-year boundary. This is a communication gap, not a pricing dispute.",
        "",
        "## Action Ideas for Product Team",
        "1. Add a pre-redemption confirmation showing applicable exit load before the user confirms.",
        "2. Surface an exit-load explainer card on the scheme page and in the FAQ with the 1-year rule in plain language.",
        "3. Add a support macro with the standardized fee explanation for agents handling redemption queries.",
    ]
    return "\n".join(lines)


def generate_fee_explainer(insights, client=None):
    client = client if client is not None else _client()
    fee = insights['fee_issue']
    label = fee['label']
    urls = fee['source_urls']
    quotes = fee['example_quotes']

    if 'exit' in fee['key']:
        facts = [
            "Exit load is a fee charged when units are redeemed before a specified holding period.",
            "For HDFC Large Cap Fund Direct Growth, the exit load is 1% if units are redeemed within 1 year of purchase.",
            "The 1-year period is counted from the date of allotment of units, not from the date of the redemption request.",
            "If units are held beyond 1 year, no exit load is applicable on redemption.",
            "The load is deducted from the redemption amount, so the amount credited is lower than the gross redemption value.",
            "The applicable exit load is scheme-specific and is published on the official scheme page and in the scheme information document.",
        ]
    else:
        facts = [
            "Expense ratio is the annual fee charged by a mutual fund scheme to cover management and operating expenses.",
            "It is expressed as a percentage of the scheme's average net assets and is deducted daily from the NAV.",
            "The expense ratio is scheme-specific and differs between direct and regular plans.",
            "It does not include exit load or other transaction charges, which are levied separately.",
            "The latest disclosed expense ratio is published on the official scheme page.",
            "Investors should refer to the official source links below for the current value for their scheme.",
        ]

    if client:
        try:
            user = f"""Fee: {label}. User confusion quotes: {quotes}. Official sources: {urls}.
Facts to use (do not add anything else): {facts}.
Write exactly 6 short neutral bullet points explaining the fee clearly. Then list the 2 source links and 'Last checked: {datetime.now().strftime("%Y-%m-%d")}'."""
            out = _llm_call(client, FEE_SYSTEM, user, max_tokens=300)
            if urls[0] not in out or urls[1] not in out:
                out += "\n\nSources:\n- " + "\n- ".join(urls)
            if "Last checked:" not in out:
                out += f"\n\nLast checked: {datetime.now().strftime('%Y-%m-%d')}"
            return out
        except Exception:
            pass

    lines = [f"### Standardized Explanation: {label}", ""]
    lines += [f"- {f}" for f in facts]
    lines += ["", "**Sources:**"]
    lines += [f"- {u}" for u in urls]
    lines += [f"", f"Last checked: {datetime.now().strftime('%Y-%m-%d')}"]
    return "\n".join(lines)


def generate_all():
    insights = analyze_reviews()
    client = _client()
    return {
        "insights": insights,
        "weekly_pulse": generate_weekly_pulse(insights, client),
        "fee_explainer": generate_fee_explainer(insights, client),
    }


if __name__ == '__main__':
    out = generate_all()
    print("PULSE:\n", out['weekly_pulse'])
    print("\nEXPLAINER:\n", out['fee_explainer'])
