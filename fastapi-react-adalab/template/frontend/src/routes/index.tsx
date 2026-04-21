import { Link, createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  component: Welcome,
});

function Welcome() {
  return (
    <div className="stack-lg">
      <div className="card welcome-hero">
        <span className="badge success">✓ Scaffolding is live</span>
        <h1>Welcome, developer.</h1>
        <p className="lead">
          If you can read this, the app is running end-to-end — backend, frontend,
          database, auth, guardrails — and is ready for you to start building.
        </p>
      </div>

      <div className="card">
        <h2>Start with Claude Code</h2>
        <p>Open this repo in Claude Code. Your first prompt:</p>
        <pre>
          <code>
            Read FEATURES_TODO.md, ask me clarifying questions until you have
            a concrete list, then propose an implementation order and start with #1.
          </code>
        </pre>
        <p className="muted">
          Claude will follow <code>.claude/rules/feature-pattern.md</code> for backend
          work and <code>.claude/rules/react-components.md</code> for the UI. It will
          run <code>/check</code> before declaring anything done, and stop without
          committing so you can review.
        </p>
      </div>

      <div className="card">
        <h2>Your first steps</h2>
        <ol className="steps">
          <li>
            Read <code>DEVELOPER_GUIDE.md</code> in the repo — a quick tour of what
            you just got.
          </li>
          <li>
            Fill in <code>FEATURES_TODO.md</code> with the features you want built.
            Claude can help you brainstorm and sharpen them.
          </li>
          <li>
            Kick off feature #1. Claude will implement, <code>/check</code>, and stop
            for your review.
          </li>
          <li>
            <strong>Remove this welcome page.</strong> It is item #1 in{' '}
            <code>FEATURES_TODO.md</code>. Replace{' '}
            <code>frontend/src/routes/index.tsx</code> with your real home (dashboard,
            redirect, whatever fits).
          </li>
        </ol>
      </div>

      <div className="welcome-grid">
        <div className="card">
          <h3>Explore the demo</h3>
          <p>
            Departments and Employees are fully wired. Projects is scaffolded but
            intentionally incomplete — it's the live-demo target for{' '}
            <code>/complete-projects</code>.
          </p>
          <div className="row" style={{ gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
            <Link to="/departments">
              <button type="button">Departments</button>
            </Link>
            <Link to="/employees">
              <button type="button">Employees</button>
            </Link>
            <Link to="/projects">
              <button type="button">Projects</button>
            </Link>
          </div>
        </div>

        <div className="card">
          <h3>Try file IO</h3>
          <p>
            Reference implementations for CSV upload analysis and CSV / Excel export
            live in Tools. Copy the pattern for your domain's data processing.
          </p>
          <Link to="/tools">
            <button type="button" className="primary">
              Open Tools
            </button>
          </Link>
        </div>

        <div className="card">
          <h3>Guardrails</h3>
          <p>
            Three layers: <code>CLAUDE.md</code> (intent),{' '}
            <code>.claude/settings.json</code> (deny rules),{' '}
            <code>.claude/hooks/protect_paths.py</code> (real enforcement).
          </p>
          <p className="muted">
            The hook blocks edits to protected files even when Claude tries a Bash
            workaround (e.g. <code>cat .env</code>).
          </p>
        </div>

        <div className="card">
          <h3>Rebrand per prospect</h3>
          <p>Two files control the brand:</p>
          <ul>
            <li>
              <code>frontend/public/logo.svg</code>
            </li>
            <li>
              <code>frontend/src/styles/tokens.css</code> (three{' '}
              <code>--color-*</code> values)
            </li>
          </ul>
          <p className="muted">
            Rebuild via AdaLab Test → Build → Deploy. No code changes needed — every
            component reads from the token variables.
          </p>
        </div>
      </div>
    </div>
  );
}
