import { useEffect, useState } from "react";
import { adminListCohorts, exportUrl, type Cohort } from "../../api";

export default function Export() {
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [cohort, setCohort] = useState("all");
  const [format, setFormat] = useState<"csv" | "parquet">("csv");
  const [history, setHistory] = useState(true);

  useEffect(() => {
    adminListCohorts().then(setCohorts).catch(() => {});
  }, []);

  const url = exportUrl(format, cohort, history);

  return (
    <div className="card">
      <h2>Export</h2>
      <p className="muted">
        Columns are named after the schema fields, so exports from different years of this
        exercise line up directly. Full history and Parquet are available to you as admin;
        students can pull latest-only CSV from the Results page.
      </p>

      <div className="toolbar">
        <label className="stack">
          <span style={{ fontWeight: 700 }}>Cohort</span>
          <select value={cohort} onChange={(e) => setCohort(e.target.value)}>
            <option value="all">All cohorts</option>
            {cohorts.map((c) => (
              <option key={c.id} value={c.label}>
                {c.label}
              </option>
            ))}
          </select>
        </label>

        <label className="stack">
          <span style={{ fontWeight: 700 }}>Format</span>
          <select value={format} onChange={(e) => setFormat(e.target.value as "csv" | "parquet")}>
            <option value="csv">CSV</option>
            <option value="parquet">Parquet</option>
          </select>
        </label>

        <label className="row" style={{ alignSelf: "center", gap: 6 }}>
          <input type="checkbox" checked={history} onChange={(e) => setHistory(e.target.checked)} />
          <span>Include full history (superseded rows)</span>
        </label>
      </div>

      <a className="btn btn-primary" href={url}>
        Download
      </a>
    </div>
  );
}
