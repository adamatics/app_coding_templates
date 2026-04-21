import { Link } from '@tanstack/react-router';

const activeClass = { className: 'sidebar-link active' };
const inactiveClass = { className: 'sidebar-link' };

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="./logo.svg" alt="Logo" className="sidebar-logo" />
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section">
          <div className="sidebar-section-label">Getting started</div>
          <Link to="/" activeProps={activeClass} inactiveProps={inactiveClass}>
            Welcome
          </Link>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Directory</div>
          <Link
            to="/departments"
            activeProps={activeClass}
            inactiveProps={inactiveClass}
          >
            Departments
          </Link>
          <Link
            to="/employees"
            activeProps={activeClass}
            inactiveProps={inactiveClass}
          >
            Employees
          </Link>
          <Link
            to="/projects"
            activeProps={activeClass}
            inactiveProps={inactiveClass}
          >
            Projects
          </Link>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Tools</div>
          <Link to="/tools" activeProps={activeClass} inactiveProps={inactiveClass}>
            Files &amp; Reports
          </Link>
        </div>
      </nav>

      <div className="sidebar-footer">
        <span className="muted">AdaLab demo template</span>
      </div>
    </aside>
  );
}
