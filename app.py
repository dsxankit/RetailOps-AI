from pathlib import Path

import streamlit as st

from ai import ask_sop_assistant, load_sops
from routing import classify_issue

BASE_DIR = Path(__file__).resolve().parent
SOP_DIR = BASE_DIR / "sops"

st.set_page_config(
    page_title="RetailOps AI (Demo)",
    page_icon="🛍️",
    layout="centered",
)


def main():
    st.title("🛍️ RetailOps Store Assistant")
    st.caption(
        "Independent demonstration project: AI-powered retail operations assistant "
        "for store policies, returns, billing, and inventory."
    )

    # Load SOP documents using absolute path
    try:
        sop_context, loaded_files = load_sops(SOP_DIR)
    except Exception as e:  # noqa: BLE001
        st.error(f"Error loading SOP files: {e}")
        st.stop()

    # Sidebar showing active SOP sources and checking file sizes via absolute paths
    with st.sidebar:
        st.header("📄 Loaded SOP Documents")
        for filename in loaded_files:
            file_path = SOP_DIR / filename
            file_size = file_path.stat().st_size if file_path.exists() else 0
            status = f"✅ ({file_size} bytes)" if file_size > 0 else "⚠️ EMPTY (0 bytes)"
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

    # Render existing chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Capture input from either the chat box or a sidebar quick-test button
    user_query = st.chat_input("Ask a policy or operational question...")
    if "pending_question" in st.session_state:
        user_query = st.session_state.pop("pending_question")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Searching store SOPs..."):
                try:
                    answer = ask_sop_assistant(user_query, sop_context)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Failed to communicate with Gemini API: {e}")

    # Objective 3: Operational Issue Classification & Routing Form
    st.divider()
    st.subheader("Report an Operational Issue")

    with st.form("issue_classification_form"):
        description = st.text_area(
            "Describe the operational problem",
            placeholder="Example: A customer wants to return a damaged item without a receipt.",
            height=100,
        )
        submitted = st.form_submit_button("Classify Issue")

    if submitted:
        if not description.strip():
            st.warning("Please enter an issue description.")
        else:
            st.session_state["classification"] = classify_issue(description)

    if "classification" in st.session_state:
        result = st.session_state["classification"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Category:** {result['category']}")
            st.markdown(f"**Responsible:** {result['assigned_to']}")
        with col2:
            st.markdown(f"**Issue Type:** {result['issue_type']}")
            sources_str = ", ".join(result["sources"]) if result["sources"] else "None"
            st.markdown(f"**SOP Sources:** {sources_str}")

        st.markdown("**Recommended Actions:**")
        for action in result["actions"]:
            st.write("-", action)

        if result["requires_review"]:
            st.warning("Manual review required.")
        else:
            st.success("Classification completed.")


if __name__ == "__main__":
    main()