"""Optional HITL UI: trace view + approve/reject for gated actions."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ragchatbot.orchestrator.pipeline import run_ticket

st.set_page_config(page_title="ragchatbot HITL", layout="wide")
st.title("ragchatbot — human-in-the-loop")

ticket_file = st.file_uploader("Ticket JSON", type=["json"])
if ticket_file:
    ticket = json.loads(ticket_file.getvalue().decode("utf-8"))
    st.subheader(ticket.get("subject", ticket.get("ticket_id")))
    st.json(ticket)

    if "run_result" not in st.session_state:
        st.session_state.run_result = None

    if st.button("Run orchestrator"):
        path = Path("_uploaded_ticket.json")
        path.write_text(json.dumps(ticket), encoding="utf-8")
        st.session_state.run_result = run_ticket(path)

    result = st.session_state.run_result
    if result:
        for step in result.trace:
            with st.expander(step.name, expanded=True):
                st.write(step.detail)
                st.json(step.data)
        st.write("### Proposed steps")
        for step in result.steps:
            st.write(step)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve action"):
                path = Path("_uploaded_ticket.json")
                st.session_state.run_result = run_ticket(path, approve_action=True)
        with col2:
            if st.button("Reject action"):
                path = Path("_uploaded_ticket.json")
                st.session_state.run_result = run_ticket(path, reject_action=True)
        st.info(f"Action status: {result.proposed_action.status.value}")
