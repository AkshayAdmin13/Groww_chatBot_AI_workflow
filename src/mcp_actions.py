"""
MCP-style tool layer with explicit human approval gating.

Simulated tools:
  1. append_to_notes_doc  -> appends a structured entry to a local Markdown doc
  2. create_email_draft   -> writes a draft .txt file (never sends)

Both tools are ONLY called after `approve()` returns True (user clicks Approve
in the Streamlit UI or types 'yes' in the CLI). This mirrors MCP tool calling
with a human-in-the-loop approval step.
"""
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DOC = os.path.join(BASE_DIR, 'output', 'notes_doc.md')
EMAIL_DRAFT = os.path.join(BASE_DIR, 'output', 'email_draft.txt')
AUDIT_LOG = os.path.join(BASE_DIR, 'output', 'mcp_audit_log.jsonl')


def build_payload(output):
    """Build the exact MCP append payload required by the brief."""
    ins = output['insights']
    fee = ins['fee_issue']
    # Collect only the bullet lines that appear before the "Sources:" section,
    # so source URLs are not mixed into explanation_bullets.
    bullets = []
    for line in output['fee_explainer'].splitlines():
        s = line.strip()
        if s.lower().startswith('**sources:**') or s.lower().startswith('sources:'):
            break
        if s.startswith('-'):
            bullets.append(s.lstrip('- ').strip())
    return {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "top_themes": [t['theme'] for t in ins['top3_themes']],
        "weekly_pulse": output['weekly_pulse'],
        "identified_fee_issue": fee['label'],
        "explanation_bullets": bullets,
        "source_links": fee['source_urls'],
    }


def _log(action, approved_by, status):
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    entry = {"timestamp": datetime.now().isoformat(), "action": action,
             "approved_by": approved_by, "status": status}
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")


def approve(approval_input, expected_phrase="APPROVE"):
    """Minimum requirement: explicit user approval before ANY MCP action."""
    return str(approval_input).strip().upper() == expected_phrase


def append_to_notes_doc(payload, approved_by="user"):
    os.makedirs(os.path.dirname(NOTES_DOC), exist_ok=True)
    entry = f"""\n\n---\n\n## Entry — {payload['date']}\n\n- **Top themes:** {', '.join(payload['top_themes'])}\n- **Fee issue:** {payload['identified_fee_issue']}\n\n### Weekly pulse\n\n{payload['weekly_pulse']}\n\n### Explanation bullets\n"""
    for b in payload['explanation_bullets']:
        entry += f"- {b}\n"
    entry += "\n### Source links\n"
    for u in payload['source_links']:
        entry += f"- {u}\n"
    with open(NOTES_DOC, 'a', encoding='utf-8') as f:
        f.write(entry)
    _log("append_to_notes_doc", approved_by, "success")
    return NOTES_DOC


def create_email_draft(payload, approved_by="user", date=None):
    date = date or payload['date']
    os.makedirs(os.path.dirname(EMAIL_DRAFT), exist_ok=True)
    subject = f"Weekly Product Pulse + Customer Clarification — {date}"
    body = f"""Subject: {subject}\n\nTo: product-team@example.com; support-team@example.com\n\nBody:\n\n{payload['weekly_pulse']}\n\n---\n\nReusable support snippet — {payload['identified_fee_issue']}\n\n"""
    for b in payload['explanation_bullets']:
        body += f"- {b}\n"
    body += "\nSources:\n"
    for u in payload['source_links']:
        body += f"- {u}\n"
    body += "\n[STATUS: DRAFT ONLY — NOT SENT]\n"
    with open(EMAIL_DRAFT, 'w', encoding='utf-8') as f:
        f.write(body)
    _log("create_email_draft", approved_by, "success")
    return EMAIL_DRAFT, subject, body


def run_approved_actions(output, approval_input, approved_by="user"):
    """Gate: never call tools unless approval is explicit."""
    if not approve(approval_input):
        _log("all_actions", approved_by, "blocked_no_approval")
        return {"status": "blocked", "message": "No valid approval. No tools were called."}
    payload = build_payload(output)
    doc_path = append_to_notes_doc(payload, approved_by)
    draft_path, subject, body = create_email_draft(payload, approved_by)
    return {
        "status": "success",
        "payload": payload,
        "notes_doc": doc_path,
        "email_draft": draft_path,
        "subject": subject,
        "body": body,
    }
