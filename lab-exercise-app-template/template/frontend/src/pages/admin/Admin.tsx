import { useEffect, useState } from "react";
import { adminLogout, adminSession } from "../../api";
import { useMeta } from "../../metaContext";
import AdminLogin from "./AdminLogin";
import Cohorts from "./Cohorts";
import GroupsAdmin from "./GroupsAdmin";
import Export from "./Export";

type Tab = "cohorts" | "groups" | "export";

export default function Admin() {
  const meta = useMeta();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [tab, setTab] = useState<Tab>("cohorts");

  useEffect(() => {
    if (!meta.admin_enabled) {
      setAuthed(false);
      return;
    }
    adminSession()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
  }, [meta.admin_enabled]);

  if (!meta.admin_enabled) {
    return (
      <div className="notice">
        The admin area is disabled because <code>ADMIN_PASSWORD</code> is not set for this
        deployment. Set it and redeploy to enable admin access.
      </div>
    );
  }
  if (authed === null) return <p className="muted">Checking…</p>;
  if (!authed) return <AdminLogin onAuthed={() => setAuthed(true)} />;

  const tabBtn = (id: Tab, label: string) => (
    <button
      className={"btn btn-small " + (tab === id ? "btn-primary" : "btn-secondary")}
      onClick={() => setTab(id)}
    >
      {label}
    </button>
  );

  return (
    <>
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="row">
            {tabBtn("cohorts", "Cohorts")}
            {tabBtn("groups", "Groups & results")}
            {tabBtn("export", "Export")}
          </div>
          <button
            className="btn btn-secondary btn-small"
            onClick={async () => {
              await adminLogout().catch(() => {});
              setAuthed(false);
            }}
          >
            Log out
          </button>
        </div>
      </div>

      {tab === "cohorts" && <Cohorts />}
      {tab === "groups" && <GroupsAdmin />}
      {tab === "export" && <Export />}
    </>
  );
}
