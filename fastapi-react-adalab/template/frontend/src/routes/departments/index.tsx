import { Link, createFileRoute } from '@tanstack/react-router';

import { useDepartments } from '../../api/departments';
import { DataTable } from '../../components/DataTable';
import type { Department } from '../../types/department';

export const Route = createFileRoute('/departments/')({
  component: DepartmentsList,
});

function DepartmentsList() {
  const { data, isPending, error } = useDepartments();

  if (isPending) return <p>Loading…</p>;
  if (error) return <p style={{ color: 'var(--color-danger)' }}>Error: {error.message}</p>;

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-lg)',
        }}
      >
        <h1>Departments</h1>
        <Link to="/departments/new">
          <button type="button" className="primary">
            + New Department
          </button>
        </Link>
      </div>
      <DataTable<Department>
        columns={[
          {
            key: 'name',
            header: 'Name',
            render: (d) => (
              <Link to="/departments/$id" params={{ id: String(d.id) }}>
                {d.name}
              </Link>
            ),
          },
          { key: 'code', header: 'Code' },
          {
            key: 'description',
            header: 'Description',
            render: (d) => d.description ?? '',
          },
        ]}
        rows={data ?? []}
        rowKey={(r) => r.id}
        emptyMessage="No departments yet. Add one to get started."
      />
    </div>
  );
}
