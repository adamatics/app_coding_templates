"""FAQ (§B3): course info, downloadable documents, and answers maintained by the teacher."""
from __future__ import annotations

import streamlit as st

from core import admin, documents as core_documents
from core.config import settings
from core.db import get_session
from core.errors import CoreError



def render() -> None:
    st.header("Course info & FAQ")
    with get_session() as session:
        faq = admin.faq_markdown(session)
        links = admin.get_setting(session, "material_links") or []
        instructor = admin.get_setting(session, "instructor") or ""
        course_name = admin.get_setting(session, "course_name") or settings.exercise_title
        docs = core_documents.list_documents(session)

    st.caption(course_name + (f" · {instructor}" if instructor else ""))

    render_documents(docs, heading="Documents you can download")

    st.subheader("Questions")
    st.markdown(faq or "_No questions answered yet — ask your instructor._")

    if links:
        st.subheader("Course material")
        for item in links:
            st.markdown(f"- [{item.get('label', item.get('url', 'link'))}]({item.get('url', '#')})")

    st.markdown("---")
    who = f"{instructor} · " if instructor else ""
    st.caption(f"Still stuck? {who}{settings.contact_email}")


def render_documents(docs: list[dict], heading: str = "Course documents",
                     key_prefix: str = "faq") -> None:
    """Shared renderer so the same downloads appear on FAQ and on Data capture."""
    if not docs:
        return
    if heading:
        st.subheader(heading)
    for doc in docs:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"**{doc['label']}**"
                    + (f"  \n{doc['description']}" if doc["description"] else "")
                    + f"  \n<span style='opacity:.7'>{doc['size_human']}</span>",
                    unsafe_allow_html=True)
        with get_session() as session:
            try:
                data, _ = core_documents.read_bytes(session, doc["id"])
            except CoreError:
                c2.caption("unavailable")
                continue
        c2.download_button("Download", data, file_name=doc["original_name"],
                           mime=doc["content_type"], key=f"{key_prefix}_dl_{doc['id']}")
