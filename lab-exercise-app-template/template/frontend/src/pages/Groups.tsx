import { useEffect, useState } from "react";
import { addMember, createGroup, listGroups, type Group } from "../api";
import { useMeta } from "../metaContext";

// Create a group (name + member names, add/remove rows before save) or append yourself to
// an existing one. No password, no lock — picking your group later IS the identification.
export default function Groups() {
  const meta = useMeta();
  const [groups, setGroups] = useState<Group[]>([]);
  const [name, setName] = useState("");
  const [members, setMembers] = useState<string[]>([""]);
  const [error, setError] = useState<string | null>(null);
  const [joinNames, setJoinNames] = useState<Record<number, string>>({});

  const openCohort = meta.open_cohort;

  function refresh() {
    listGroups().then(setGroups).catch((e) => setError(String(e.message ?? e)));
  }
  useEffect(refresh, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createGroup(name.trim(), members.map((m) => m.trim()).filter(Boolean));
      setName("");
      setMembers([""]);
      refresh();
    } catch (err: any) {
      setError(err.message ?? String(err));
    }
  }

  async function onJoin(groupId: number) {
    const value = (joinNames[groupId] ?? "").trim();
    if (!value) return;
    setError(null);
    try {
      await addMember(groupId, value);
      setJoinNames((p) => ({ ...p, [groupId]: "" }));
      refresh();
    } catch (err: any) {
      setError(err.message ?? String(err));
    }
  }

  if (!openCohort) {
    return (
      <div className="notice">
        There is no open cohort right now, so new groups can't be created. Ask your
        instructor to open one.
      </div>
    );
  }

  return (
    <>
      {error && <div className="notice">{error}</div>}

      <div className="card">
        <h2>Make a new group</h2>
        <form onSubmit={onCreate}>
          <div className="field">
            <label htmlFor="gname">Group name</label>
            <input id="gname" value={name} onChange={(e) => setName(e.target.value)} required />
            <span className="help">Pick something your group will recognise later.</span>
          </div>

          <div className="field">
            <label>Members</label>
            {members.map((m, i) => (
              <div key={i} className="row" style={{ marginBottom: 6 }}>
                <input
                  value={m}
                  placeholder={`Member ${i + 1}`}
                  onChange={(e) => setMembers((prev) => prev.map((x, j) => (j === i ? e.target.value : x)))}
                />
                {members.length > 1 && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => setMembers((prev) => prev.filter((_, j) => j !== i))}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => setMembers((prev) => [...prev, ""])}
            >
              Add another member
            </button>
          </div>

          <button type="submit" className="btn btn-primary">
            Create group
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Groups in {openCohort}</h2>
        {groups.length === 0 && <p className="muted">No groups yet — be the first!</p>}
        {groups.map((g) => (
          <div key={g.id} style={{ borderTop: "1px solid var(--mint)", paddingTop: 12, marginTop: 12 }}>
            <strong>{g.name}</strong>
            <div className="muted" style={{ margin: "4px 0" }}>
              {g.members.length ? g.members.map((m) => m.display_name).join(", ") : "no members yet"}
            </div>
            <div className="row">
              <input
                placeholder="Add your name to this group"
                value={joinNames[g.id] ?? ""}
                onChange={(e) => setJoinNames((p) => ({ ...p, [g.id]: e.target.value }))}
              />
              <button className="btn btn-secondary btn-small" onClick={() => onJoin(g.id)}>
                Join
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
