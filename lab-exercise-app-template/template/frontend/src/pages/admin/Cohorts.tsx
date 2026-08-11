import { useEffect, useState } from "react";
import {
  adminCloseCohort,
  adminListCohorts,
  adminOpenCohort,
  adminSeedDemo,
  type Cohort,
} from "../../api";
import { useMeta } from "../../metaContext";
import ConfirmButton from "../../components/ConfirmButton";
import DataTable, { type Column } from "../../components/DataTable";

export default function Cohorts() {
  const meta = useMeta();
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  function refresh() {
    adminListCohorts().then(setCohorts).catch((e) => setError(String(e.message ?? e)));
  }
  useEffect(refresh, []);
  const openCohort = cohorts.find((c) => c.status === "open");

  async function wrap(fn: () => Promise<unknown>, done?: string) {
    setError(null);
    setMsg(null);
    try {
      await fn();
      if (done) setMsg(done);
      refresh();
    } catch (e: any) {
      setError(e.message ?? String(e));
    }
  }

  const columns: Column<Cohort>[] = [
    { key: "label", label: "Cohort" },
    { key: "status", label: "Status" },
    { key: "group_count", label: "Groups" },
    { key: "result_count", label: "Results" },
    { key: "created_at", label: "Opened", render: (c) => new Date(c.created_at).toLocaleDateString() },
    {
      key: "closed_at",
      label: "Closed",
      render: (c) => (c.closed_at ? new Date(c.closed_at).toLocaleDateString() : "—"),
    },
  ];

  return (
    <>
      {error && <div className="notice">{error}</div>}
      {msg && <div className="notice">{msg}</div>}

      <div className="card">
        <h2>Cohorts</h2>
        <DataTable columns={columns} rows={cohorts} rowKey={(c) => c.id} />
      </div>

      <div className="card">
        <h2>Open a new cohort</h2>
        {openCohort ? (
          <p className="muted">
            Cohort <strong>{openCohort.label}</strong> is open. Close it before opening a new one —
            closing keeps all its data, it just makes it read-only.
          </p>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              wrap(() => adminOpenCohort(label.trim()), `Opened ${label.trim()}.`).then(() => setLabel(""));
            }}
          >
            <div className="field">
              <label htmlFor="label">New cohort label</label>
              <input id="label" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. 2027-spring" />
            </div>
            <button className="btn btn-primary" type="submit">
              Open cohort
            </button>
          </form>
        )}
      </div>

      {openCohort && (
        <div className="card">
          <h2>Close the open cohort (reset for a new class)</h2>
          <p className="muted">
            This closes <strong>{openCohort.label}</strong>. Its groups and results stay fully
            visible and exportable — nothing is deleted. Then open a new cohort for the next class.
          </p>
          <ConfirmButton
            label={`Close ${openCohort.label}`}
            confirmLabel="Close this cohort? Data is kept, writes stop."
            onConfirm={() => wrap(() => adminCloseCohort(), `Closed ${openCohort.label}.`)}
          />
        </div>
      )}

      {meta.demo_mode && (
        <div className="card">
          <h2>Demo data</h2>
          <p className="muted">Seeds two synthetic prior cohorts so the compare view has something to show.</p>
          <button
            className="btn btn-secondary"
            onClick={() => wrap(async () => {
              const r = await adminSeedDemo();
              setMsg(`Seeded: ${r.created_cohorts.join(", ") || "nothing new"}`);
            })}
          >
            Seed demo cohorts
          </button>
        </div>
      )}
    </>
  );
}
