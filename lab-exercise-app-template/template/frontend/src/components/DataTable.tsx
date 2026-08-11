import type { ReactNode } from "react";

// Generic chassis table. Columns are derived from the schema field order by the caller,
// so the results table follows the schema automatically (spec §10).

export interface Column<Row> {
  key: string;
  label: string;
  render?: (row: Row) => ReactNode;
}

interface Props<Row> {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string | number;
  empty?: string;
}

export default function DataTable<Row>({ columns, rows, rowKey, empty }: Props<Row>) {
  if (rows.length === 0) {
    return <p className="muted">{empty ?? "Nothing here yet."}</p>;
  }
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td key={c.key}>
                  {c.render ? c.render(row) : formatCell((row as Record<string, unknown>)[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}
