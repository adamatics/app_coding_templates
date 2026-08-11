import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listGroups, submitResult, type Group, type Payload } from "../api";
import { useMeta } from "../metaContext";
import SchemaForm from "../components/SchemaForm";

// Pick your group, fill the schema-generated form, submit, and see your values echoed back.
export default function EnterResults() {
  const meta = useMeta();
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState<string>("");
  const [saved, setSaved] = useState<Payload | null>(null);
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    listGroups().then(setGroups).catch(() => {});
  }, []);

  const labels = useMemo(
    () => Object.fromEntries(meta.field_order.map((n) => [n, meta.schema.properties[n]?.title ?? n])),
    [meta],
  );

  if (!meta.open_cohort) {
    return <div className="notice">There is no open cohort right now, so results can't be entered.</div>;
  }

  return (
    <>
      <div className="card">
        <h2>Enter a result</h2>
        <div className="field">
          <label htmlFor="grp">Your group</label>
          <select id="grp" value={groupId} onChange={(e) => setGroupId(e.target.value)}>
            <option value="">Choose your group…</option>
            {groups.map((g) => (
              <option key={g.id} value={String(g.id)}>
                {g.name}
              </option>
            ))}
          </select>
          {groups.length === 0 && (
            <span className="help">
              No groups yet — <Link to="/groups">create one first</Link>.
            </span>
          )}
          <span className="help">Choosing your group is how the app knows the result is yours.</span>
        </div>

        {groupId !== "" && (
          <SchemaForm
            key={formKey}
            schema={meta.schema}
            fieldOrder={meta.field_order}
            submitLabel="Submit result"
            onSubmit={async (payload) => {
              const res = await submitResult(Number(groupId), payload);
              setSaved(res.values);
              setFormKey((k) => k + 1);
            }}
          />
        )}
      </div>

      {saved && (
        <div className="card">
          <h2>Saved ✓</h2>
          <p>Here's what we stored for you:</p>
          <div className="table-wrap">
            <table className="table">
              <tbody>
                {meta.field_order.map((name) =>
                  saved[name] === undefined ? null : (
                    <tr key={name}>
                      <th style={{ width: "40%" }}>{labels[name]}</th>
                      <td>{String(saved[name])}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
          <button className="btn btn-secondary" onClick={() => setSaved(null)}>
            Enter another
          </button>
        </div>
      )}
    </>
  );
}
