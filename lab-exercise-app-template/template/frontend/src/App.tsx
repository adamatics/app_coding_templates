import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { getMeta, type Meta } from "./api";
import { MetaContext } from "./metaContext";
import logoWide from "./assets/logo-wide.svg";
import mark from "./assets/mark.svg";
import Home from "./pages/Home";
import Groups from "./pages/Groups";
import EnterResults from "./pages/EnterResults";
import Results from "./pages/Results";
import Admin from "./pages/admin/Admin";

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const isAdmin = location.pathname.startsWith("/admin");

  useEffect(() => {
    getMeta()
      .then((m) => {
        setMeta(m);
        document.title = `${m.exercise_title} · CPDSE`;
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) {
    return (
      <div className="container">
        <div className="notice">Could not load the app: {error}</div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="container" style={{ textAlign: "center", paddingTop: 80 }}>
        <img src={mark} alt="" width={48} height={48} />
        <p className="muted">Loading…</p>
      </div>
    );
  }

  return (
    <MetaContext.Provider value={meta}>
      <div className="app">
        <header className={"app-header" + (isAdmin ? " admin" : "")}>
          <div className="header-row">
            {!isAdmin && <img className="brand-logo" src={logoWide} alt="CPDSE" />}
            <h1 className="brand-title">
              {meta.exercise_title}
              <span className="course-code"> · {meta.course_code}</span>
            </h1>
            {isAdmin && <span className="admin-tag">Admin</span>}
          </div>
          <nav className="nav">
            <NavLink to="/" end>
              Home
            </NavLink>
            <NavLink to="/groups">Groups</NavLink>
            <NavLink to="/enter">Enter results</NavLink>
            <NavLink to="/results">Results</NavLink>
            <NavLink to="/admin" className="nav-admin">
              Admin
            </NavLink>
          </nav>
        </header>

        <main className="container">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/groups" element={<Groups />} />
            <Route path="/enter" element={<EnterResults />} />
            <Route path="/results" element={<Results />} />
            <Route path="/admin/*" element={<Admin />} />
          </Routes>
        </main>

        <footer className="footer">
          <div>
            {meta.institution_name} · {meta.course_code} ·{" "}
            <a href={`mailto:${meta.contact_email}`}>{meta.contact_email}</a>
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            A safe space to learn data science.
          </div>
        </footer>
      </div>
    </MetaContext.Provider>
  );
}
