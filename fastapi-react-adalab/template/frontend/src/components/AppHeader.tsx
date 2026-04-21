import { Link } from '@tanstack/react-router';

export function AppHeader() {
  return (
    <header
      style={{
        background: 'var(--color-primary)',
        color: 'var(--color-on-primary)',
        padding: 'var(--space-md) var(--space-xl)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-md)',
      }}
    >
      <img src="./logo.svg" alt="Logo" style={{ height: 32 }} />
      <nav
        style={{
          display: 'flex',
          gap: 'var(--space-md)',
          marginLeft: 'auto',
        }}
      >
        <Link to="/" style={{ color: 'var(--color-on-primary)' }}>
          Home
        </Link>
        <Link to="/departments" style={{ color: 'var(--color-on-primary)' }}>
          Departments
        </Link>
        <Link to="/employees" style={{ color: 'var(--color-on-primary)' }}>
          Employees
        </Link>
        <Link to="/projects" style={{ color: 'var(--color-on-primary)' }}>
          Projects
        </Link>
      </nav>
    </header>
  );
}
