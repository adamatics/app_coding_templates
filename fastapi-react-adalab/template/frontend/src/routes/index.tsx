import { Link, createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  component: Home,
});

function Home() {
  return (
    <div>
      <h1>AdaLab Demo</h1>
      <p>Directory app for Departments, Employees, and Projects.</p>
      <nav
        style={{
          display: 'flex',
          gap: 'var(--space-md)',
          marginTop: 'var(--space-lg)',
        }}
      >
        <Link
          to="/departments"
          style={{
            padding: 'var(--space-md)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          Departments
        </Link>
        <Link
          to="/employees"
          style={{
            padding: 'var(--space-md)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          Employees
        </Link>
        <Link
          to="/projects"
          style={{
            padding: 'var(--space-md)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          Projects
        </Link>
      </nav>
    </div>
  );
}
