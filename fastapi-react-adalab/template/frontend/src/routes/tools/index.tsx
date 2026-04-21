import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';

import { apiClient } from '../../api/client';

export const Route = createFileRoute('/tools/')({
  component: Tools,
});

interface CsvAnalysis {
  filename: string;
  rows: number;
  columns: number;
  headers: string[];
  preview: string[][];
}

function Tools() {
  const [analysis, setAnalysis] = useState<CsvAnalysis | null>(null);
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const result = await apiClient.upload<CsvAnalysis>(
        '/reports/analyze-csv',
        file,
      );
      setAnalysis(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (path: string, filename: string) => {
    setDownloading(filename);
    setError(null);
    try {
      await apiClient.download(path, filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="stack-lg">
      <div>
        <h1>Files &amp; Reports</h1>
        <p className="lead">
          Reference implementations for file upload and CSV / Excel download.
          Copy the pattern for your domain's data processing.
        </p>
      </div>

      <div className="card">
        <h2>Analyze a CSV</h2>
        <p>
          Upload a CSV and the backend returns its shape. Wired to{' '}
          <code>POST /api/reports/analyze-csv</code>. To accept{' '}
          <code>.xlsx</code> instead, swap the stdlib <code>csv</code> parser
          in <code>app/services/reports.py</code> for <code>openpyxl</code>.
        </p>

        <input
          type="file"
          accept=".csv"
          disabled={uploading}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleUpload(f);
          }}
        />

        {uploading && (
          <p className="muted" style={{ marginTop: 'var(--space-sm)' }}>
            Analyzing…
          </p>
        )}

        {analysis && (
          <div className="stack-md" style={{ marginTop: 'var(--space-md)' }}>
            <div className="row" style={{ flexWrap: 'wrap' }}>
              <span className="badge info">{analysis.filename}</span>
              <span className="muted">
                {analysis.rows} rows × {analysis.columns} columns
              </span>
            </div>

            {analysis.preview.length > 0 && (
              <table>
                <thead>
                  <tr>
                    {analysis.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {analysis.preview.map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {analysis.preview.length === 0 && (
              <p className="muted">
                File parsed but had no data rows below the header.
              </p>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h2>Download reports</h2>
        <p>
          Export the employee roster with a joined department name column.
          Wired to <code>GET /api/reports/employees.csv</code> and{' '}
          <code>GET /api/reports/employees.xlsx</code>.
        </p>
        <div className="row" style={{ gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="primary"
            disabled={downloading === 'employees.csv'}
            onClick={() => handleDownload('/reports/employees.csv', 'employees.csv')}
          >
            {downloading === 'employees.csv' ? 'Downloading…' : 'Download CSV'}
          </button>
          <button
            type="button"
            disabled={downloading === 'employees.xlsx'}
            onClick={() =>
              handleDownload('/reports/employees.xlsx', 'employees.xlsx')
            }
          >
            {downloading === 'employees.xlsx'
              ? 'Downloading…'
              : 'Download Excel'}
          </button>
        </div>
        <p className="muted" style={{ marginTop: 'var(--space-md)' }}>
          Downloads go through <code>apiClient.download()</code> so they carry
          the Bearer token — a plain <code>&lt;a download&gt;</code> would skip
          auth and 401.
        </p>
      </div>

      {error && (
        <div
          className="card"
          style={{
            borderColor: 'var(--color-danger)',
            background: 'var(--color-danger-bg)',
          }}
        >
          <strong style={{ color: 'var(--color-danger)' }}>Error:</strong>{' '}
          <span className="muted">{error}</span>
        </div>
      )}
    </div>
  );
}
