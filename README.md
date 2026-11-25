# Groww AI Workflow — Feedback → Product Pulse → Customer Clarification

**Milestone 05 (AI Workflows)** built on top of the **Milestone 04 RAG FAQ assistant** (Groww Mutual Funds). This workflow transforms raw customer reviews into a structured internal update and a ready-to-use customer communication, with an **MCP-style approval gate** before any action is taken.

---

## What this workflow does

```
Reviews CSV → Review Intelligence → Weekly Product Pulse
                                ↘ Fee Explainer (from detected confusion)
                                          → ⛔ APPROVAL GATE
                                                 → Append to Notes Doc
                                                 → Create Email Draft (no auto-send)
```

1. **Review Intelligence** — clusters 30 public reviews (10 weeks) into max 5 themes, surfaces top 3 themes and 3 real quotes, and detects one recurring fee confusion.
2. **Weekly Product Pulse** — ≤250-word structured internal note (themes, quotes, key observation, 3 action ideas).
3. **Fee Explainer** — ≤6 bullet, facts-only explanation with 2 official source links and `Last checked:`.
4. **MCP Actions (approval-gated)** — appends to a notes doc and creates an email draft, only after explicit user approval.

### Fee issue identified from reviews
**Exit load (1% if redeemed within 1 year)** — mentioned in **12 of 30 reviews**, with users frequently describing it as unexpected or unclear at redemption time (e.g. “The exit load FAQ says 1% within 1 year but I redeemed on day 364. Still charged.”). The explainer directly addresses this confusion.

---

## Deliverables / files

| File | Description |
|---|---|
| `app/app.py` | Streamlit prototype (4 tabs: Intelligence, Pulse, Explainer, MCP) — default entrypoint |
| `app/workflow_app.py` | Same workflow (alternate entrypoint) |
| `src/review_intelligence.py` | Step 1 — clustering, quotes, fee detection |
| `src/workflow_generate.py` | Steps 2 & 3 — pulse + explainer generation (Groq with local fallback) |
| `src/mcp_actions.py` | Approval-gated MCP tools + audit log |
| `data/reviews/customer_reviews.csv` | 30 public reviews over 10 weeks (sample) |
| `output/weekly_product_pulse.md` | Generated weekly pulse |
| `output/fee_explainer.md` | Generated fee explainer |
| `output/notes_doc.md` | Notes/Doc showing appended entry (after approval) |
| `output/email_draft.txt` | Email draft text (draft only, never sent) |
| `output/source_list.md` | 6 official source URLs |
| `app/faq_app.py` + `src/` | Milestone 4 RAG FAQ assistant (base product) |

---

## How to run

```bash
# 1. Clone and install
git clone https://github.com/AkshayAdmin13/Groww_chatBot_AI_workflow.git
cd Groww_chatBot_AI_workflow
pip install -r requirements.txt

# 2. (Optional) add Groq key for LLM-generated wording
cp .env.example .env
# edit .env -> GROQ_API_KEY=your_key

# 3. Launch the workflow prototype (default entrypoint)
streamlit run app/app.py

# Alternative entrypoint (same workflow):
streamlit run app/workflow_app.py

# To run the Milestone 4 FAQ assistant:
streamlit run app/faq_app.py
```

**To generate static outputs without the UI:**
```bash
python -c "import sys; sys.path.insert(0,'src'); from workflow_generate import generate_all; print(generate_all()['weekly_pulse'])"
```

---

## Where MCP approval happens

In `app/app.py` → tab **4 · MCP Actions**:

- The exact append payload (date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links) is displayed as JSON.
- A text input requires the user to type **`APPROVE`**.
- `src/mcp_actions.py::approve()` checks this; if it is not `APPROVE`, **no tool is called** and the audit log records `blocked_no_approval`.
- Only after approval do the two simulated MCP tools run:
  1. `append_to_notes_doc()` → writes `output/notes_doc.md`
  2. `create_email_draft()` → writes `output/email_draft.txt` (marked **DRAFT ONLY — NOT SENT**)
- Every action is recorded in `output/mcp_audit_log.jsonl`.

CLI equivalent:
```python
from mcp_actions import run_approved_actions
result = run_approved_actions(output, "APPROVE")  # anything else is blocked
```

---

## Source list (official)

1. https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
2. https://groww.in/mutual-funds/amc/hdfc-mutual-funds
3. https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
4. https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
5. https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
6. https://www.amfiindia.com/investor-corner/knowledge-center

---

## Disclaimer

This is a simulated internal product + support workflow for demonstration purposes. Review data is illustrative. Fee explanations are facts-only and based on official public pages; no investment advice, recommendations, or performance claims are made. The email step never sends messages — it only creates a draft. No personal information is collected.
