"""
Streamlit UI for the AI Workflow:
Review Intelligence -> Weekly Pulse -> Fee Explainer -> MCP approval-gated actions.
"""
import os
import sys
from datetime import datetime

import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'src'))

from workflow_generate import generate_all
from mcp_actions import build_payload, run_approved_actions, approve, NOTES_DOC, EMAIL_DRAFT, AUDIT_LOG

st.set_page_config(page_title="Groww Feedback → Action Workflow", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .block { background: #ffffff; color: #1f1f1f; padding: 1.1rem; border-radius: 12px;
             border-left: 4px solid #00d09c; margin: 0.6rem 0; box-shadow: 0 2px 6px rgba(0,0,0,.05); }
    .quote { background: #fff8e1; color: #6b5200; padding: .8rem; border-radius: 8px;
             border-left: 4px solid #ffc107; margin: .4rem 0; }
    .gate { background: #fff3f3; color: #8a1c1c; padding: 1rem; border-radius: 12px;
            border: 1px solid #ef9a9a; margin: 1rem 0; }
    h1, h2, h3 { color: #1f1f1f; }
    @media (prefers-color-scheme: dark) {
        .stApp, [data-testid="stAppViewContainer"] { background: #0e1117 !important; }
        h1,h2,h3,h4,p,li,label,.stMarkdown { color: #f8fafc !important; }
        .block { background: #1f232b !important; color: #f8fafc !important; }
        .quote { background: #3d341f !important; color: #ffd93d !important; }
        .gate { background: #3d1f1f !important; color: #ffb4b4 !important; border-color: #ef9a9a !important; }
        .stTextInput input { color: #f8fafc !important; background: #1f232b !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Groww Feedback → Action Workflow")
st.caption("Milestone 05 · AI workflow that converts customer reviews into a product pulse + customer clarification, with MCP approval gating.")

if st.button("▶ Run workflow", type="primary"):
    with st.spinner("Analyzing reviews..."):
        st.session_state.output = generate_all()
    st.success("Workflow complete")

out = st.session_state.get("output")

if out:
    ins = out['insights']
    fee = ins['fee_issue']

    t1, t2, t3, t4 = st.tabs(["1 · Review Intelligence", "2 · Weekly Pulse", "3 · Fee Explainer", "4 · MCP Actions"])

    with t1:
        st.subheader("Review Intelligence Layer")
        c1, c2, c3 = st.columns(3)
        c1.metric("Reviews analyzed", ins['total_reviews'])
        c2.metric("Period", "10 weeks")
        c3.metric("Fee issue mentions", fee['mentions'])
        st.markdown("**Detected themes (max 5):**")
        for i, t in enumerate(ins['themes'], 1):
            st.markdown(f"<div class='block'>{i}. <b>{t['theme']}</b> — {t['count']} reviews ({t['share_pct']}%), avg rating {t['avg_rating']}/5</div>", unsafe_allow_html=True)
        st.markdown("**Real user quotes:**")
        for q in ins['quotes']:
            st.markdown(f"<div class='quote'>“{q['text']}” <br><small>— {q['review_id']}, {q['date']}, {q['rating']}/5</small></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='block'><b>Recurring fee confusion:</b> {fee['label']} ({fee['mentions']} mentions)</div>", unsafe_allow_html=True)

    with t2:
        st.subheader("Weekly Product Pulse (≤250 words)")
        st.caption(f"Word count: {len(out['weekly_pulse'].split())}")
        st.markdown(out['weekly_pulse'])
        st.download_button("Download pulse (.md)", out['weekly_pulse'], file_name="weekly_product_pulse.md")

    with t3:
        st.subheader("Fee Explainer (derived from review insights)")
        st.markdown(out['fee_explainer'])
        st.download_button("Download explainer (.md)", out['fee_explainer'], file_name="fee_explainer.md")

    with t4:
        st.subheader("MCP Actions — Approval Gated")
        st.markdown("<div class='gate'><b>Gate:</b> No document write or email draft is created until you explicitly type <code>APPROVE</code> below.</div>", unsafe_allow_html=True)
        st.json(build_payload(out))
        approval = st.text_input("Type APPROVE to allow MCP tools:", placeholder="APPROVE")
        if st.button("Execute MCP actions", type="primary"):
            result = run_approved_actions(out, approval)
            if result['status'] == 'blocked':
                st.error(result['message'])
            else:
                st.success("✅ Approved — both MCP tools executed")
                st.markdown(f"- Appended to doc: `{result['notes_doc']}`")
                st.markdown(f"- Email draft created: `{result['email_draft']}`")
                st.markdown(f"- Subject: **{result['subject']}**")
                with st.expander("Preview email draft"):
                    st.text(result['body'])
                if os.path.exists(AUDIT_LOG):
                    with st.expander("Audit log"):
                        st.text(open(AUDIT_LOG, encoding='utf-8').read())
else:
    st.info("Click **Run workflow** to analyze reviews and generate outputs.")
