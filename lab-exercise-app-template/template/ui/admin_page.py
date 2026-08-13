"""Admin (§B3, §B6): course settings, cohort lifecycle, groups/members, exports, event log.

Fail-closed: with no ADMIN_PASSWORD the area is disabled and says so.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import admin as core_admin, cohorts, documents as core_documents, events
from core import export as core_export, identity
from core import results as results_core
from core import storage
from core.config import settings
from core.db import get_session
from core.errors import CoreError
from core.models import Member

from . import _components as C


def render() -> None:
    st.header("Admin")
    if not settings.admin_enabled:
        C.notice("The admin area is disabled because <code>ADMIN_PASSWORD</code> is not set for "
                 "this deployment. Set it and redeploy to enable admin access.", "err")
        return

    if not st.session_state.get("is_admin"):
        with st.form("admin_login"):
            pw = st.text_input("Admin password", type="password")
            ok = st.form_submit_button("Sign in")
        if ok:
            if core_admin.verify_admin_password(pw):
                st.session_state["is_admin"] = True
                with get_session() as session:
                    events.log(session, "admin_login", actor="admin")
                st.rerun()
            else:
                C.notice("Incorrect password.", "err")
        return

    if st.button("Sign out of admin"):
        st.session_state.pop("is_admin", None)
        st.rerun()

    tabs = st.tabs(["Course", "Years", "Groups & results", "Export", "Log"])
    with tabs[0]:
        _course_tab()
    with tabs[1]:
        _years_tab()
    with tabs[2]:
        _groups_tab()
    with tabs[3]:
        _export_tab()
    with tabs[4]:
        _log_tab()


SCOPE_HELP = {
    "own": "own — a student sees only their own readings",
    "group": "group — their own group's readings",
    "neighbour": "neighbour — their group plus one neighbouring group",
    "hold": "hold — everyone in their hold",
    "year": "year — the whole class this year",
    "all": "all — every year the app has run (needed for cross-year comparison)",
}


def _course_tab() -> None:
    with get_session() as session:
        current = core_admin.all_settings(session)

    st.subheader("Course setup")
    st.caption("Everything on this tab is visible to students immediately after you save. "
               "Nothing here touches their data.")

    # --- identity -----------------------------------------------------------
    with st.expander("① Course name and instructor — who this app belongs to", expanded=True):
        st.markdown(
            "Shown on the FAQ page and on every exported report, so a student who finds a PDF "
            "months later can tell which course and which teacher it came from.")
        course_name = st.text_input("Course name", value=current.get("course_name", ""),
                                    help="e.g. 'Farmaceutisk kemi — logP-øvelse'")
        instructor = st.text_input("Instructor", value=current.get("instructor", ""),
                                   help="Name (and email if you want) students should contact.")

    # --- banner -------------------------------------------------------------
    with st.expander("② Message to the class — a banner on every page", expanded=True):
        st.markdown(
            "**Use this for something that changes mid-session** and everyone must see: "
            "*'Fridge A is broken — use fridge C'*, *'Skip step 4 today'*, "
            "*'Hand in before 15:00'*.\n\n"
            "It appears at the top of **every page**, for **every student**, as soon as you "
            "save — they see it on their next click, no reload needed. "
            "**Leave it empty to remove the banner.** Keep it to one or two sentences; it is "
            "not the place for standing instructions (those belong in the exercise "
            "instructions or the FAQ below).")
        banner = st.text_area("Banner text (empty = no banner)",
                              value=current.get("banner", ""), height=80,
                              placeholder="Use fridge C — fridge A is broken.")
        if (current.get("banner") or "").strip():
            st.caption("A banner is currently showing to students.")

    # --- FAQ ----------------------------------------------------------------
    with st.expander("③ FAQ — answer the recurring question once", expanded=False):
        st.markdown(
            "Every year the same questions come back: *'Which pipette?'*, *'What if my value "
            "is negative?'*, *'Can I submit twice?'*. Answer them here and they are on the "
            "**FAQ page** for every student, this year and next.\n\n"
            "Written in **Markdown**: `## Heading`, `**bold**`, `- bullet`, "
            "`[link text](https://…)`. Add to it during the session — when two groups ask the "
            "same thing, that is the signal.")
        faq_md = st.text_area("FAQ content (Markdown)", value=current.get("faq_md", ""),
                              height=220)
        with st.popover("Preview"):
            st.markdown(faq_md or "_Empty_")

    # --- comparison scope ---------------------------------------------------
    with st.expander("④ How much data may students compare against?", expanded=False):
        st.markdown(
            "On the analysis page students pick what to compare their numbers with. This sets "
            "**the widest choice they are allowed** — they can always choose something "
            "narrower. Comparison views are anonymised either way: distributions and summary "
            "statistics, never names or group labels.\n\n"
            "Pick **all** for the usual case (comparing with previous years is most of the "
            "point). Pick something narrower if you want groups working independently first.")
        for scope in results_core.SCOPE_ORDER:
            st.markdown(f"- {SCOPE_HELP[scope]}")
        max_scope = st.selectbox(
            "Widest comparison students may choose", results_core.SCOPE_ORDER,
            index=results_core.SCOPE_ORDER.index(current.get("max_scope", "all")),
            format_func=lambda s: SCOPE_HELP[s])

    # --- identity layers ----------------------------------------------------
    with st.expander("⑤ Do students work in groups?", expanded=False):
        st.markdown(
            "**On (normal):** students join or create a group of 2–3 when they register, and "
            "results belong to the group.\n\n"
            "**Off:** each student works alone — the group step disappears from registration "
            "and everyone gets their own private bench. Turn this off only for individual "
            "exercises; changing it mid-course confuses students who already registered.")
        group_layer = st.checkbox(
            "Students work in groups", key="cfg_group_layer",
            value=bool((current.get("active_layers") or {}).get("group", True)))

    if st.button("Save course settings", type="primary"):
        with get_session() as session:
            core_admin.set_setting(session, "course_name", course_name)
            core_admin.set_setting(session, "instructor", instructor)
            core_admin.set_setting(session, "banner", banner)
            core_admin.set_setting(session, "max_scope", max_scope)
            core_admin.set_setting(session, "faq_md", faq_md)
            layers = dict(current.get("active_layers") or {})
            layers["group"] = group_layer
            core_admin.set_setting(session, "active_layers", layers)
        C.notice("Saved. Students see the change on their next click.", "ok")

    st.markdown("---")
    _documents_section()


def _documents_section() -> None:
    """Upload the øvelsesvejledning and anything else students should be able to download."""
    st.subheader("⑥ Documents for students")
    st.markdown(
        "Upload the **øvelsesvejledning** (lab manual), a data sheet, a worked example — "
        "anything students should be able to download. They appear on the **FAQ page** and in "
        "a *Course documents* panel on the **Data capture** page, so a student who forgot the "
        "manual can get it while standing at the bench.\n\n"
        f"PDF works best. Maximum {core_documents.human_size(core_documents.MAX_DOCUMENT_BYTES)} "
        "per file — for anything larger (a video, a big dataset), put it elsewhere and add a "
        "link in the FAQ instead. Files are stored on the course volume, so they survive "
        "redeploys and are still there next year.")

    with get_session() as session:
        docs = core_documents.list_documents(session)

    with st.form("upload_document", clear_on_submit=True):
        upload = st.file_uploader("Choose a file", type=None,
                                  help="PDF, Word, Excel, images, CSV — whatever students need.")
        c1, c2 = st.columns(2)
        label = c1.text_input("Title students will see",
                              placeholder="e.g. Øvelsesvejledning — logP")
        description = c2.text_input("One-line description (optional)",
                                    placeholder="e.g. Read section 3 before you start")
        do_upload = st.form_submit_button("Upload")
    if do_upload:
        if upload is None:
            C.notice("Choose a file first.", "err")
        else:
            with get_session() as session:
                try:
                    core_documents.save(session, upload.getvalue(), upload.name,
                                        label=label, description=description)
                except CoreError as exc:
                    C.notice(exc.message, "err")
                else:
                    C.notice(f"Uploaded — students can download it now.", "ok")
                    st.rerun()

    if not docs:
        st.caption("No documents yet.")
        return

    st.markdown("**Uploaded so far** — students see these in this order.")
    for doc in docs:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{doc['label']}**  \n"
                        f"{doc['description'] or '_no description_'}  \n"
                        f"`{doc['original_name']}` · {doc['size_human']} · "
                        f"uploaded {doc['uploaded_at'][:10]}")
            with get_session() as session:
                try:
                    data, _ = core_documents.read_bytes(session, doc["id"])
                except CoreError as exc:
                    c2.caption("file missing")
                    C.notice(exc.message, "err")
                    data = None
            if data is not None:
                c2.download_button("Download", data, file_name=doc["original_name"],
                                   mime=doc["content_type"], key=f"dl_{doc['id']}")
            if c3.button("Remove", key=f"rm_{doc['id']}"):
                st.session_state[f"confirm_rm_{doc['id']}"] = True
            if st.session_state.get(f"confirm_rm_{doc['id']}"):
                C.notice("Remove this document? Students will no longer see it. "
                         "(This deletes teaching material only — never student data.)")
                d1, d2 = st.columns(2)
                if d1.button("Confirm remove", key=f"crm_{doc['id']}"):
                    with get_session() as session:
                        core_documents.delete(session, doc["id"])
                    st.session_state.pop(f"confirm_rm_{doc['id']}", None)
                    st.rerun()
                if d2.button("Cancel", key=f"canc_{doc['id']}"):
                    st.session_state.pop(f"confirm_rm_{doc['id']}", None)
                    st.rerun()


def _years_tab() -> None:
    with get_session() as session:
        rows = cohorts.list_cohorts(session)
        open_cohort = cohorts.get_open_cohort(session)
    st.subheader("Years (cohorts)")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Closing a year makes it read-only. Its data stays fully visible and "
               "exportable — nothing is ever deleted.")

    if open_cohort:
        st.write(f"Open year: **{open_cohort.label}**")
        if st.session_state.get("confirm_close"):
            C.notice("Close this year? Students can no longer submit. Data is kept.")
            c1, c2 = st.columns(2)
            if c1.button("Confirm close"):
                with get_session() as session:
                    cohorts.close_open_cohort(session)
                st.session_state.pop("confirm_close", None)
                st.rerun()
            if c2.button("Cancel"):
                st.session_state.pop("confirm_close", None)
                st.rerun()
        elif st.button(f"Close {open_cohort.label}"):
            st.session_state["confirm_close"] = True
            st.rerun()
    else:
        with st.form("open_year"):
            label = st.text_input("New year label", placeholder="e.g. 2027")
            ok = st.form_submit_button("Open year")
        if ok:
            with get_session() as session:
                try:
                    cohorts.create_cohort(session, label)
                except CoreError as exc:
                    C.notice(exc.message, "err")
                    return
            st.rerun()

    if settings.demo_mode and st.button("Seed demo years"):
        from core.seed_demo import seed_demo_data
        with get_session() as session:
            created = seed_demo_data(session)
        C.notice(f"Seeded: {', '.join(created) or 'nothing new'}", "ok")


def _groups_tab() -> None:
    with get_session() as session:
        all_years = cohorts.list_cohorts(session)
    if not all_years:
        st.caption("No years yet.")
        return
    labels = [c["label"] for c in all_years]
    year = st.selectbox("Year", labels)
    with get_session() as session:
        cohort = cohorts.get_cohort_by_label(session, year)
        groups = identity.list_groups(session, cohort)
        group_rows = []
        for g in groups:
            members = session.query(Member).filter(Member.group_id == g.id).all()
            group_rows.append({"id": g.id, "hold": g.hold, "group": g.name,
                               "members": ", ".join(f"{m.display_name} ({m.kuid})" for m in members)})
        rows = results_core.query_results(session, group_ids=[g.id for g in groups], latest=False)

    st.subheader("Groups")
    st.dataframe(pd.DataFrame(group_rows), use_container_width=True, hide_index=True)

    if groups:
        names = {f"{g.name} (id {g.id})": g.id for g in groups}
        c1, c2 = st.columns(2)
        with c1:
            src = st.selectbox("Group", list(names), key="grp_src")
            new_name = st.text_input("Rename to")
            if st.button("Rename") and new_name:
                with get_session() as session:
                    try:
                        core_admin.rename_group(session, names[src], new_name)
                    except CoreError as exc:
                        C.notice(exc.message, "err")
                st.rerun()
        with c2:
            tgt = st.selectbox("Merge into", list(names), key="grp_tgt")
            if st.button("Merge"):
                with get_session() as session:
                    try:
                        core_admin.merge_groups(session, names[src], names[tgt])
                    except CoreError as exc:
                        C.notice(exc.message, "err")
                st.rerun()

    st.subheader("Results (full history)")
    if rows:
        frame = pd.DataFrame([{**results_core.flat_rows([r])[0], "id": r["id"]} for r in rows])
        st.dataframe(frame, use_container_width=True, hide_index=True)
        rid = st.number_input("Hard-delete result id (single bogus row; audited)",
                              min_value=0, step=1, value=0)
        if rid and st.button("Delete result"):
            with get_session() as session:
                try:
                    results_core.hard_delete_result(session, int(rid))
                except CoreError as exc:
                    C.notice(exc.message, "err")
            st.rerun()
    else:
        st.caption("No results in this year.")


def _export_tab() -> None:
    st.subheader("Export")
    if not settings.storage_is_durable:
        C.notice(
            "<b>This app is not writing to a Shared Volume, so an export is the only lasting "
            "copy.</b> Download the database below at the end of every session — a redeploy "
            "or restart erases everything stored in the app.", "err")
    st.caption("Columns are the schema fields plus year/hold/group/kuid/submitted_at/superseded, "
               "so exports from different years line up directly.")
    with get_session() as session:
        years = [c["label"] for c in cohorts.list_cohorts(session)]
    scope = st.selectbox("Year", ["All years"] + years)
    history = st.checkbox("Include full history (superseded rows)", value=True)
    with get_session() as session:
        if scope == "All years":
            rows = results_core.query_results(session, latest=not history)
        else:
            cohort = cohorts.get_cohort_by_label(session, scope)
            gids = [g.id for g in identity.list_groups(session, cohort)]
            rows = results_core.query_results(session, group_ids=gids, latest=not history)
    base = f"{settings.project_slug}_{'all' if scope == 'All years' else scope}"
    cohort_id = None
    if scope != "All years":
        with get_session() as session:
            cohort_id = cohorts.get_cohort_by_label(session, scope).id

    def _log(fmt: str):
        """Admin exports are logged too — same as the student ones (on click, not on render)."""
        def handler():
            with get_session() as session:
                core_export.log_export(session, fmt, actor="admin", scope=scope, rows=len(rows))
        return handler

    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    st.markdown("**Measurements**")
    c1, c2 = st.columns(2)
    c1.download_button("CSV", core_export.to_csv(rows), file_name=f"{base}.csv",
                       mime="text/csv", on_click=_log("csv"))
    c2.download_button("Excel", core_export.to_excel(rows), file_name=f"{base}.xlsx",
                       mime=XLSX, on_click=_log("excel"))

    st.markdown("**Everything else**")
    st.caption("The free-text answers and the roster live only in the report otherwise — these "
               "put them in a spreadsheet you can grade from.")
    with get_session() as session:
        answers_csv = core_export.to_answers_csv(session, cohort_id)
        workbook = core_export.build_workbook(session, rows, cohort_id)
    c3, c4 = st.columns(2)
    c3.download_button("Answers (CSV)", answers_csv, file_name=f"{base}_answers.csv",
                       mime="text/csv", on_click=_log("answers_csv"))
    c4.download_button("Full workbook (Excel)", workbook, file_name=f"{base}_full.xlsx",
                       mime=XLSX, on_click=_log("workbook"),
                       help="Sheets: results · answers · roster · years · log")

    st.markdown("**Backup**")
    st.caption("A consistent snapshot of the whole database — take one before closing a year, "
               "or before the app is retired. Contains personal data; store it accordingly. "
               "Note: uploaded documents are files on the volume and are **not** inside this "
               "snapshot — keep your own copies of those (you uploaded them, so you have them).")
    try:
        st.download_button("Download database (SQLite)", core_export.backup_sqlite(),
                           file_name=f"{base}_backup.sqlite",
                           mime="application/vnd.sqlite3", on_click=_log("sqlite_backup"))
    except Exception as exc:
        C.notice("The database snapshot could not be created.", "err")
        with get_session() as session:
            events.log_error(session, "backup_failed", exc, detail={"scope": scope})

    st.caption(f"Volume files (platform artifacts filtered): "
               f"{', '.join(storage.list_volume_dir(settings.app_data_dir)) or '—'}")


def _log_tab() -> None:
    """Event log (§B6): registrations, submissions, overwrites, exports, admin actions, errors."""
    st.subheader("Event log")
    st.caption("Append-only record of what happened: who registered and when, every "
               "submission, every correction (with what changed), exports taken, admin "
               "actions and errors. Also written to the container log and to "
               "`events.jsonl` on the volume, which survives redeploys.")

    with get_session() as session:
        known_actions = events.action_names(session)
        counts = events.counts_by_action(session)

    c1, c2, c3, c4 = st.columns([1, 1.4, 1, 1])
    level = c1.selectbox("Level", ["all", events.INFO, events.WARNING, events.ERROR])
    action = c2.selectbox("Action", ["all"] + known_actions)
    kuid = c3.text_input("KUID")
    limit = c4.number_input("Rows", min_value=50, max_value=5000, value=500, step=50)

    with get_session() as session:
        rows = events.recent(
            session, limit=int(limit),
            level=None if level == "all" else level,
            action=None if action == "all" else action,
            kuid=kuid.strip() or None,
        )

    errors = sum(v for k, v in counts.items() if k.endswith("_failed"))
    st.caption(f"{sum(counts.values())} events recorded · "
               f"{counts.get('student_registered', 0)} registrations · "
               f"{counts.get('result_submitted', 0)} submissions · "
               f"{counts.get('result_superseded', 0)} corrections · "
               f"{counts.get('export_generated', 0)} exports · "
               f"{errors} failures")

    frame = pd.DataFrame(rows)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    if not frame.empty:
        st.download_button("Download log (CSV)", frame.to_csv(index=False).encode("utf-8"),
                           file_name=f"{settings.project_slug}_events.csv", mime="text/csv")
