from pathlib import Path
import streamlit as st
from ai import load_sops, ask_sop_assistant
from analytics import get_analytics
from database import (
    STATUSES,
    create_ticket,
    get_ticket,
    init_db,
    list_tickets,
    update_ticket_status,
)
from routing import classify_issue

BASE_DIR = Path(__file__).resolve().parent
SOP_DIR = BASE_DIR / "sops"

st.set_page_config(
    page_title="RetailOps AI (Demo)",
    page_icon="🛍️",
    layout="wide",  # Wide layout gives tables and side-by-side charts breathing room
)


def main():
    init_db()

    st.title("🛍️ RetailOps Store Assistant")
    st.caption(
        "Independent demonstration project: AI-powered retail operations assistant "
        "for store policies, issue routing, ticket tracking, and operational analytics."
    )

    # Load SOP documents using absolute path
    try:
        sop_context, loaded_files = load_sops(SOP_DIR)
    except Exception as e:
        st.error(f"Error loading SOP files: {e}")
        st.stop()

    # Sidebar: Active SOP sources & Quick Test Prompts
    with st.sidebar:
        st.header("📄 Loaded SOP Documents")
        for filename in loaded_files:
            file_path = SOP_DIR / filename
            file_size = file_path.stat().st_size if file_path.exists() else 0
            status = f"✅ ({file_size} B)" if file_size > 0 else "⚠️ EMPTY"
            st.markdown(f"- `{filename}` — {status}")

        if not sop_context.strip() or all((SOP_DIR / f).stat().st_size == 0 for f in loaded_files):
            st.error("Your `sops/*.md` files are empty! Paste the SOP text into them and save.")

        st.divider()
        st.subheader("🧪 Quick Test Questions")
        sample_questions = [
            "Can I return clothes without a receipt?",
            "Can a customer return a damaged product without a receipt?",
            "What is the refund method for online purchases?",
            "Can a customer use a coupon on innerwear?",
            "What is the Wi-Fi password for the breakroom?",
        ]
        for q in sample_questions:
            if st.button(q, use_container_width=True):
                st.session_state.pending_question = q

        st.divider()
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! Ask me any question regarding store returns, billing, or inventory SOPs.",
            }
        ]

    # Create 3 clean workspace tabs
    tab_chat, tab_tickets, tab_analytics = st.tabs([
        "💬 SOP Assistant",
        "🚨 Issue Reporting & Tickets",
        "📊 Business Analytics & ROI",
    ])

    # ==========================================
    # TAB 1: SOP ASSISTANT (CHAT)
    # ==========================================
    with tab_chat:
        st.subheader("Store Policy & SOP Lookup")

        chat_container = st.container(height=450)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_query = st.chat_input("Ask a policy or operational question...")
        if "pending_question" in st.session_state:
            user_query = st.session_state.pop("pending_question")

        if user_query:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_query)

                with st.chat_message("assistant"):
                    with st.spinner("Searching store SOPs..."):
                        try:
                            answer = ask_sop_assistant(user_query, sop_context)
                            st.markdown(answer)
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                        except Exception as e:
                            st.error(f"Failed to communicate with local Ollama model: {e}")

    # ==========================================
    # TAB 2: ISSUE CLASSIFICATION & TICKETS
    # ==========================================
    with tab_tickets:
        left_col, right_col = st.columns([1, 1.2], gap="large")

        with left_col:
            st.subheader("Report an Operational Issue")

            with st.form("issue_classification_form"):
                description = st.text_area(
                    "Describe the operational problem",
                    placeholder="Example: A customer wants to return a damaged item without a receipt.",
                    height=100,
                )
                submitted = st.form_submit_button("Classify Issue", use_container_width=True)

            if submitted:
                if not description.strip():
                    st.warning("Please describe the issue.")
                    st.session_state.pop("pending_ticket", None)
                else:
                    result = classify_issue(description)
                    st.session_state["classification"] = result
                    st.session_state["pending_ticket"] = {
                        "description": description.strip(),
                        "result": result,
                    }

            if "classification" in st.session_state:
                result = st.session_state["classification"]

                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Category:** {result['category']}")
                    c1.markdown(f"**Responsible:** {result['assigned_to']}")
                    c2.markdown(f"**Issue Type:** {result['issue_type']}")
                    sources_str = ", ".join(result["sources"]) if result["sources"] else "None"
                    c2.markdown(f"**SOP Sources:** {sources_str}")

                    st.markdown("**Recommended Actions:**")
                    for action in result["actions"]:
                        st.write("-", action)

                    if result["requires_review"]:
                        st.warning("Manual review required.")
                    else:
                        st.success("Classification completed.")

            created_id = st.session_state.pop("created_ticket_id", None)
            if created_id is not None:
                st.success(f"✅ Ticket #{created_id} created successfully.")

            if "pending_ticket" in st.session_state:
                pending = st.session_state["pending_ticket"]
                result = pending["result"]

                with st.container(border=True):
                    st.markdown("#### Confirm Ticket Creation")
                    st.write("**Problem:**", pending["description"])
                    st.write("**Category:**", result["category"])
                    st.write("**Issue Type:**", result["issue_type"])
                    st.write("**Assigned To:**", result["assigned_to"])

                    if result["requires_review"]:
                        st.warning(
                            "This issue requires manual review. "
                            "It will be saved without an assigned owner."
                        )

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("Create Ticket", type="primary", use_container_width=True):
                            try:
                                ticket_id = create_ticket(pending["description"], result)
                                del st.session_state["pending_ticket"]
                                st.session_state["created_ticket_id"] = ticket_id
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ticket creation failed: {e}")

                    with btn_col2:
                        if st.button("Cancel", use_container_width=True):
                            del st.session_state["pending_ticket"]
                            st.rerun()

        with right_col:
            st.subheader("Ticket Management")

            tickets = list_tickets()
            if not tickets:
                st.info("No tickets have been created yet.")
            else:
                st.dataframe(
                    tickets,
                    use_container_width=True,
                    hide_index=True,
                )

                tickets_by_id = {ticket["id"]: ticket for ticket in tickets}
                selected_id = st.selectbox(
                    "Select Ticket to Update",
                    options=list(tickets_by_id),
                    format_func=lambda ticket_id: (
                        f"#{ticket_id} - {tickets_by_id[ticket_id]['issue_type']} "
                        f"({tickets_by_id[ticket_id]['status']})"
                    ),
                )

                selected_ticket = get_ticket(selected_id)
                if selected_ticket:
                    with st.form("update_status_form"):
                        st.write(
                            f"**Current Status:** `{selected_ticket['status']}` | "
                            f"**Assigned To:** `{selected_ticket['assigned_to']}`"
                        )
                        current_index = STATUSES.index(selected_ticket["status"])
                        new_status = st.selectbox(
                            "New Status",
                            options=STATUSES,
                            index=current_index,
                        )
                        update_clicked = st.form_submit_button(
                            "Update Ticket Status",
                            use_container_width=True,
                        )

                    if update_clicked:
                        if update_ticket_status(selected_id, new_status):
                            st.rerun()
                        else:
                            st.error("Ticket was not found.")

    # ==========================================
    # TAB 3: BUSINESS ANALYTICS & ROI
    # ==========================================
    with tab_analytics:
        st.subheader("Business Analytics Dashboard")

        stats = get_analytics()

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Tickets", stats["total"])
        k2.metric("Open", stats["open"])
        k3.metric("In Progress", stats["in_progress"])
        k4.metric("Resolved", stats["resolved"])
        k5.metric("Resolution Rate", f"{stats['resolution_rate']}%")

        df = stats["data"]
        if not df.empty:
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("#### Issues by Category")
                category_counts = (
                    df["category"]
                    .value_counts()
                    .rename_axis("Category")
                    .reset_index(name="Tickets")
                )
                st.bar_chart(category_counts, x="Category", y="Tickets")

            with chart_col2:
                st.markdown("#### Tickets by Status")
                status_counts = (
                    df["status"]
                    .value_counts()
                    .rename_axis("Status")
                    .reset_index(name="Tickets")
                )
                st.bar_chart(status_counts, x="Status", y="Tickets")

            st.metric("Tickets Requiring Manual Review", stats["manual_review"])
        else:
            st.info("Create some tickets in the 'Issue Reporting & Tickets' tab to view analytics.")

        st.divider()
        st.subheader("Potential Time Savings (ROI Estimator)")
        st.caption("Scenario estimates only, not measured pilot results.")

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            queries = st.number_input("Monthly SOP queries", min_value=0, value=200)
        with r2:
            manual_time = st.number_input("Manual lookup (min)", min_value=0.0, value=5.0)
        with r3:
            ai_time = st.number_input("AI lookup (min)", min_value=0.0, value=1.0)
        with r4:
            hours_saved = queries * max(0.0, manual_time - ai_time) / 60.0
            st.metric("Estimated Hours Saved / Month", f"{hours_saved:.1f} hrs")


if __name__ == "__main__":
    main()