import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/projects/')({
  component: ProjectsStub,
});

function ProjectsStub() {
  return (
    <div>
      <h1>Projects</h1>
      <p style={{ color: 'var(--color-muted)', maxWidth: 640 }}>
        Coming soon. The Projects feature is scaffolded in the backend
        (see <code>app/models/project.py</code>) but its routes, service,
        schemas, and UI are intentionally incomplete.
      </p>
      <p style={{ color: 'var(--color-muted)', maxWidth: 640 }}>
        Run the <code>/complete-projects</code> command in Claude Code to
        implement the full CRUD live during a demo, mirroring the
        Departments and Employees patterns.
      </p>
    </div>
  );
}
