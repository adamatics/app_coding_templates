import { Link, createFileRoute } from '@tanstack/react-router';

import { useDepartments } from '../../api/departments';
import { useEmployees } from '../../api/employees';
import { DataTable } from '../../components/DataTable';
import type { Employee } from '../../types/employee';

export const Route = createFileRoute('/employees/')({
  component: EmployeesList,
});

function EmployeesList() {
  const employees = useEmployees();
  const departments = useDepartments();

  if (employees.isPending || departments.isPending) return <p>Loading…</p>;
  if (employees.error)
    return <p style={{ color: 'var(--color-danger)' }}>Error: {employees.error.message}</p>;

  const departmentById = new Map((departments.data ?? []).map((d) => [d.id, d]));

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
        <h1>Employees</h1>
        <Link to="/employees/new">
          <button type="button" className="primary">
            + New Employee
          </button>
        </Link>
      </div>
      <DataTable<Employee>
        columns={[
          {
            key: 'name',
            header: 'Name',
            render: (e) => (
              <Link to="/employees/$id" params={{ id: String(e.id) }}>
                {e.first_name} {e.last_name}
              </Link>
            ),
          },
          { key: 'email', header: 'Email' },
          { key: 'title', header: 'Title' },
          {
            key: 'department',
            header: 'Department',
            render: (e) => departmentById.get(e.department_id)?.name ?? '—',
          },
          {
            key: 'is_active',
            header: 'Active',
            render: (e) => (e.is_active ? 'Yes' : 'No'),
          },
        ]}
        rows={employees.data ?? []}
        rowKey={(r) => r.id}
        emptyMessage="No employees yet. Add one to get started."
      />
    </div>
  );
}
