import { useEffect, useState } from "react";
import type { ResultRow } from "../api";

// Minimal dependency-free SVG bar chart (spec keeps the bundle simple). Colours come from
// the theme via CSS classes only. For multi-year comparison the current cohort reads as
// foreground (Forest) and prior cohorts recede (Mint), per §13.

interface Props {
  results: ResultRow[];
  numericFields: string[];
  fieldLabels: Record<string, string>;
  scope: string; // "all" or a cohort label
  currentCohort: string | null;
}

export default function Chart({ results, numericFields, fieldLabels, scope, currentCohort }: Props) {
  const [field, setField] = useState(numericFields[0] ?? "");
  useEffect(() => {
    if (!numericFields.includes(field)) setField(numericFields[0] ?? "");
  }, [numericFields, field]);

  if (numericFields.length === 0) {
    return <p className="muted">No numeric fields to chart for this exercise.</p>;
  }

  const byCohort = scope === "all";
  const buckets = new Map<string, number[]>();
  for (const r of results) {
    const v = Number(r.values[field]);
    if (!Number.isFinite(v)) continue;
    const key = byCohort ? r.cohort : r.group;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(v);
  }
  const entries = [...buckets.entries()]
    .map(([label, vals]) => ({
      label,
      mean: vals.reduce((a, b) => a + b, 0) / vals.length,
      n: vals.length,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

  const W = Math.max(360, entries.length * 96);
  const H = 260;
  const pad = { top: 24, right: 16, bottom: 54, left: 44 };
  const means = entries.map((e) => e.mean);
  const domainMin = Math.min(0, ...means);
  const domainMax = Math.max(0.0001, ...means);
  const plotH = H - pad.top - pad.bottom;
  const plotW = W - pad.left - pad.right;
  const y = (v: number) =>
    pad.top + plotH - ((v - domainMin) / (domainMax - domainMin)) * plotH;
  const bandW = entries.length ? plotW / entries.length : plotW;
  const barW = Math.min(56, bandW * 0.6);

  return (
    <div className="chart">
      <div className="toolbar">
        <label className="stack">
          <span style={{ fontWeight: 700 }}>Series</span>
          <select value={field} onChange={(e) => setField(e.target.value)}>
            {numericFields.map((f) => (
              <option key={f} value={f}>
                {fieldLabels[f] ?? f}
              </option>
            ))}
          </select>
        </label>
        {byCohort && (
          <div className="row" style={{ fontSize: "0.85rem" }}>
            <span>
              <span className="badge" style={{ background: "var(--forest)", color: "var(--soft-white)" }}>
                &nbsp;
              </span>{" "}
              current cohort
            </span>
            <span>
              <span className="badge">&nbsp;</span> previous
            </span>
          </div>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="muted">No data to chart yet.</p>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Mean ${fieldLabels[field] ?? field}`}>
          <line className="axis-line" x1={pad.left} y1={y(domainMin)} x2={W - pad.right} y2={y(domainMin)} />
          <text className="axis-text" x={6} y={pad.top}>
            {domainMax.toFixed(2)}
          </text>
          {entries.map((e, i) => {
            const cx = pad.left + bandW * i + bandW / 2;
            const top = y(e.mean);
            const base = y(domainMin);
            const cls = byCohort
              ? e.label === currentCohort
                ? "bar-current"
                : "bar-prior"
              : `bar-${i % 5}`;
            return (
              <g key={e.label}>
                <rect
                  className={cls}
                  x={cx - barW / 2}
                  y={Math.min(top, base)}
                  width={barW}
                  height={Math.abs(base - top)}
                  rx={3}
                />
                <text className="bar-label" x={cx} y={Math.min(top, base) - 5} textAnchor="middle">
                  {e.mean.toFixed(2)}
                </text>
                <text className="axis-text" x={cx} y={H - pad.bottom + 16} textAnchor="middle">
                  {e.label}
                </text>
                <text className="axis-text" x={cx} y={H - pad.bottom + 32} textAnchor="middle">
                  n={e.n}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
