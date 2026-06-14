"""Streamlit entry point — thin UI layer over the orchestrator.

All business logic lives in ``core`` / ``providers``. This module only wires the
UI: a persona/language sidebar, an attraction reference, and a chat surface that
calls :func:`core.orchestrator.process_query`. Dependencies are built once per
session and passed explicitly.
"""

from __future__ import annotations

import streamlit as st

from core.analytics import AnalyticsStore
from core.config import load_settings
from core.exceptions import AskAbuDhabiError
from core.kb_loader import load_knowledge_base
from core.orchestrator import process_query
from core.schema import AskRequest, KBStatus, Language, Persona
from providers.factory import create_provider

_PERSONA_LABELS = {
    Persona.FIRST_TIME: "First-time visitor",
    Persona.FAMILY: "Family",
    Persona.BUSINESS: "Business traveller",
}
_LANGUAGE_LABELS = {None: "Auto-detect", Language.EN: "English", Language.AR: "العربية"}


def _bootstrap() -> None:
    """Build and cache settings, provider, attractions, and analytics once."""
    if "settings" in st.session_state:
        return
    settings = load_settings()
    attractions, kb_status = load_knowledge_base(settings)
    st.session_state.settings = settings
    st.session_state.provider = create_provider(settings)
    st.session_state.attractions = attractions
    st.session_state.kb_status = kb_status
    st.session_state.analytics = AnalyticsStore(settings.analytics_db_path)
    st.session_state.setdefault("messages", [])


def _render_sidebar() -> tuple[Persona, Language | None]:
    """Render sidebar controls and return the chosen persona and language."""
    with st.sidebar:
        st.header("⚙️ Settings")
        persona = st.selectbox(
            "Persona",
            options=list(_PERSONA_LABELS.keys()),
            format_func=lambda p: _PERSONA_LABELS[p],
        )
        language = st.selectbox(
            "Response language",
            options=list(_LANGUAGE_LABELS.keys()),
            format_func=lambda l: _LANGUAGE_LABELS[l],
        )
        if st.button("🔄 Reset chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        kb_status: KBStatus = st.session_state.kb_status
        if kb_status is KBStatus.STALE:
            st.warning("Knowledge base is STALE — data may be outdated.")
        elif kb_status is KBStatus.BASELINE:
            st.info("Serving the bundled BASELINE knowledge base.")
        else:
            st.success("Knowledge base: FRESH")

        with st.expander("📍 12 attractions & topics"):
            for attraction in st.session_state.attractions.values():
                st.markdown(f"- **{attraction.title}** · {attraction.category}")

        st.caption("Tip: ask in Arabic for an Arabic reply, or force a language above.")
    return persona, language


def _render_history() -> None:
    """Render the existing chat transcript."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("official_url"):
                st.link_button("Official site", message["official_url"])


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(page_title="Ask Abu Dhabi", page_icon="🕌", layout="centered")
    _bootstrap()
    st.title("🕌 Ask Abu Dhabi")
    st.caption("Your multilingual (EN/AR) guide to the Emirate of Abu Dhabi.")

    persona, language = _render_sidebar()
    _render_history()

    prompt = st.chat_input("Ask about mosques, museums, beaches, transport, visas…")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    request = AskRequest(query=prompt, persona=persona, language=language)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                response = process_query(
                    request,
                    provider=st.session_state.provider,
                    settings=st.session_state.settings,
                    attractions=st.session_state.attractions,
                    kb_status=st.session_state.kb_status,
                    analytics=st.session_state.analytics,
                )
            except AskAbuDhabiError as exc:
                error_text = f"⚠️ Sorry, something went wrong: {exc}"
                st.error(error_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_text}
                )
                return

        st.markdown(response.answer)
        if response.official_url:
            st.link_button("Official site", response.official_url)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "official_url": response.official_url,
        }
    )


if __name__ == "__main__":
    main()
