import { useEffect, useMemo, useState } from "react";
import {
  exportUrl,
  getAnalysis,
  getResults,
  listCohorts,
  supersedeResult,
  type Analysis,
  type Cohort,
  type ResultRow,
} from "../api";
import { useMeta } from "../metaContext";
import DataTable, { type Column } from "../components/DataTable";
import Chart from "../components/Chart";
import SchemaForm from "../components/SchemaForm";

type TableRow = Record<string, unknown> & {
  __id: number;
  __group: string;
  __cohort: string;
  __submitted: string;
  __row: ResultRow;
};

export default function Results() {
  const meta = useMeta();
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [scope, setScope] = useState<string>(meta.open_cohort ?? "all");
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [correcting, setCorrecting] = useState<ResultRow | null>(null);
  const [error, setError] = useState<string | null>(null);

  const labels = useMemo(
    () => Object.fromEntries(meta.field_order.map((n) => [n, meta.schema.properties[n]?.title ?? n])),
    [meta],
  );

  function refresh() {
    getResults(scope, true).then(setRows).catch((e) => setError(String(e.message ?? e)));
    getAnalysis(scope).then(setAnalysis).catch(() => setAnalysis(null));
  }
  useEffect(() => {
    listCohorts().then(setCohorts).catch(() => {});
  }, []);
  useEffect(refresh, [scope]);

  const tableRows: TableRow[] = rows.map((r) => ({
    ...r.values,
    __id: r.id,
    __group: r.group,
    __cohort: r.cohort,
    __submitted: r.submitted_at,
    __row: r,
  }));

  const columns: Column<TableRow>[] = [
    ...meta.field_order.map((name) => ({ key: name, label: labels[name] })),
    { key: "__group", label: "Group" },
    ...(scope === "all" ? [{ key: "__cohort", label: "Cohort" } as Column<TableRow>] : []),
    {
      key: "__submitted",
      label: "Submitted",
      render: (r) => new Date(r.__submitted).toLocaleDateString(),
    },
    {
      key: "__act",
      label: "",
      render: (r) =>
        r.__cohort === meta.open_cohort ? (
          <button className="btn btn-secondary btn-small" onClick={() => setCorrecting(r.__row)}>
            Correct
          </button>
        ) : null,
    },
  ];

  return (
    <>
      {error && <div className="notice">{error}</div>}

      <div className="card">
        <div className="toolbar">
          <label className="stack">
            <span style={{ fontWeight: 700 }}>Cohort</span>
            <select value={scope} onChange={(e) => setScope(e.target.value)}>
              <option value="all">All years</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.label}>
                  {c.label}
                  {c.status === "open" ? " (open)" : ""}
                </option>
              ))}
            </select>
          </label>
          <a className="btn btn-secondary" href={exportUrl("csv", scope, false)}>
            Download CSV
          </a>
        </div>

        <DataTable
          columns={columns}
          rows={tableRows}
          rowKey={(r) => r.__id}
          empty="No results yet for this cohort."
        />
      </div>

      {correcting && (
        <div className="card">
          <h2>Correct a reading</h2>
          <p className="muted">
            This won't erase the old value — it records a correction that replaces it, keeping an
            honest history.
          </p>
          <SchemaForm
            schema={meta.schema}
            fieldOrder={meta.field_order}
            initial={correcting.values}
            submitLabel="Submit correction"
            onSubmit={async (payload) => {
              await supersedeResult(correcting.id, payload);
              setCorrecting(null);
              refresh();
            }}
          />
          <button className="btn btn-secondary btn-small" onClick={() => setCorrecting(null)}>
            Cancel
          </button>
        </div>
      )}

      <div className="card">
        <h2>Chart</h2>
        <Chart
          results={rows}
          numericFields={meta.numeric_fields}
          fieldLabels={labels}
          scope={scope}
          currentCohort={meta.open_cohort}
        />
      </div>

      {analysis && (
        <div className="card">
          <h2>Summary</h2>
          <p>
            {String(analysis.chassis.n_results ?? 0)} latest result(s) from{" "}
            {String(analysis.chassis.n_groups ?? 0)} group(s).
          </p>
          {analysis.exercise && Object.keys(analysis.exercise).length > 0 && (
            <ul>
              {Object.entries(analysis.exercise).map(([k, v]) => (
                <li key={k}>
                  <strong>{k}:</strong> {String(v)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}
