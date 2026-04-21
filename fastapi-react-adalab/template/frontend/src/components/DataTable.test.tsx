import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DataTable } from './DataTable';

interface Row {
  id: number;
  name: string;
}

const columns = [
  { key: 'name', header: 'Name' },
  { key: 'id', header: 'ID' },
];

describe('DataTable', () => {
  it('renders empty state', () => {
    render(
      <DataTable<Row> columns={columns} rows={[]} rowKey={(r) => r.id} emptyMessage="nothing here" />,
    );
    expect(screen.getByText(/nothing here/i)).toBeInTheDocument();
  });

  it('renders rows with header and cells', () => {
    render(
      <DataTable<Row>
        columns={columns}
        rows={[
          { id: 1, name: 'Alpha' },
          { id: 2, name: 'Beta' },
        ]}
        rowKey={(r) => r.id}
      />,
    );
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });
});
