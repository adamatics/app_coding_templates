import { useEffect, useMemo, useState } from "react";
import {
  adminDeleteGroup,
  adminDeleteMember,
  adminDeleteResult,
  adminListCohorts,
  adminListGroups,
  adminMergeGroups,
  adminRenameGroup,
  getResults,
  type Cohort,
  type Group,
  type ResultRow,
} from "../../api";
import { useMeta } from "../../metaContext";
import ConfirmButton from "../../components/ConfirmButton";
import DataTable, { type Column } from "../../components/DataTable";

export default function GroupsAdmin() {
  const meta = useMeta();
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [cohort, setCohort] = useState<string>("");
  const [groups, setGroups] = useState<Group[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [renaming, setRenaming] = useState<Record<number, string>>({});
  const [mergeTarget, setMergeTarget] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const labels = useMemo(
    () => Object.fromEntries(meta.field_order.map((n) => [n, meta.schema.properties[n]?.title ?? n])),
    [meta],
  );

  useEffect(() => {
    adminListCohorts()
      .then((cs) => {
        setCohorts(cs);
        setCohort((cur) => cur || cs.find((c) => c.status === "open")?.label || cs[0]?.label || "");
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  function refresh() {
    if (!cohort) return;
    adminListGroups(cohort).then(setGroups).catch((e) => setError(String(e.message ?? e)));
    getResults(cohort, false).then(setResults).catch(() => setResults([]));
  }
  useEffect(refresh, [cohort]);

  async function wrap(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      refresh();
    } catch (e: any) {
      setError(e.message ?? String(e));
    }
  }

  const resultColumns: Column<ResultRow>[] = [
    { key: "id", label: "ID" },
    { key: "group", label: "Group" },
    ...meta.field_order.map((name) => ({
      key: name,
      label: labels[name],
      render: (r: ResultRow) => String(r.values[name] ?? "—"),
    })),
    { key: "superseded", label: "Superseded", render: (r: ResultRow) => (r.superseded ? "yes" : "no") },
    {
      key: "__act",
      label: "",
      render: (r: ResultRow) => (
        <ConfirmButton
          label="Delete"
          confirmLabel="Hard-delete this row? This is the only destructive action."
          onConfirm={() => wrap(() => adminDeleteResult(r.id))}
        />
      ),
    },
  ];

  return (
    <>
      {error && <div className="notice">{error}</div>}

      <div className="card">
        <div className="toolbar">
          <label className="stack">
            <span style={{ fontWeight: 700 }}>Cohort</span>
            <select value={cohort} onChange={(e) => setCohort(e.target.value)}>
              {cohorts.map((c) => (
                <option key={c.id} value={c.label}>
                  {c.label}
                  {c.status === "open" ? " (open)" : ""}
                </option>
              ))}
            </select>
          </label>
        </div>

        <h2>Groups</h2>
        {groups.length === 0 && <p className="muted">No groups in this cohort.</p>}
        {groups.map((g) => (
          <div key={g.id} style={{ borderTop: "1px solid var(--mint)", paddingTop: 12, marginTop: 12 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>{g.name}</strong>
              <ConfirmButton
                label="Delete group"
                confirmLabel="Delete this (empty) group?"
                onConfirm={() => wrap(() => adminDeleteGroup(g.id))}
              />
            </div>

            <div className="muted" style={{ margin: "6px 0" }}>
              {g.members.length === 0 && "no members"}
              {g.members.map((m) => (
                <span key={m.id} className="badge" style={{ marginRight: 6 }}>
                  {m.display_name}{" "}
                  <button
                    className="btn btn-danger btn-small"
                    style={{ padding: "0 6px", marginLeft: 4 }}
                    title="Remove member"
                    onClick={() => wrap(() => adminDeleteMember(m.id))}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="row" style={{ gap: 16 }}>
              <span className="row">
                <input
                  placeholder="Rename to…"
                  value={renaming[g.id] ?? ""}
                  onChange={(e) => setRenaming((p) => ({ ...p, [g.id]: e.target.value }))}
                />
                <button
                  className="btn btn-secondary btn-small"
                  onClick={() => wrap(() => adminRenameGroup(g.id, (renaming[g.id] ?? "").trim()))}
                >
                  Rename
                </button>
              </span>

              <span className="row">
                <select
                  value={mergeTarget[g.id] ?? ""}
                  onChange={(e) => setMergeTarget((p) => ({ ...p, [g.id]: e.target.value }))}
                >
                  <option value="">Merge into…</option>
                  {groups
                    .filter((o) => o.id !== g.id)
                    .map((o) => (
                      <option key={o.id} value={String(o.id)}>
                        {o.name}
                      </option>
                    ))}
                </select>
                <button
                  className="btn btn-secondary btn-small"
                  disabled={!mergeTarget[g.id]}
                  onClick={() => wrap(() => adminMergeGroups(g.id, Number(mergeTarget[g.id])))}
                >
                  Merge
                </button>
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Results (full history)</h2>
        <p className="muted">Hard-delete is only for bogus rows and is always audited.</p>
        <DataTable columns={resultColumns} rows={results} rowKey={(r) => r.id} empty="No results in this cohort." />
      </div>
    </>
  );
}
