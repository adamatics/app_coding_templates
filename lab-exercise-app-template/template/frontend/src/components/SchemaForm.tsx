import { useMemo, useState } from "react";
import { ApiError, type JsonSchema, type JsonSchemaProp, type Payload } from "../api";

// SchemaForm renders the results-entry form entirely from the JSON Schema of
// exercise/schema.py — number/text/select/date inputs, with units and ranges as help text
// and client-side validation mirroring the server. This is why adding a field to the
// schema makes it appear in the form automatically (spec §10). CHASSIS.

type InputKind = "number" | "integer" | "text" | "textarea" | "date" | "select" | "checkbox";

interface Field {
  name: string;
  label: string;
  description?: string;
  required: boolean;
  kind: InputKind;
  options?: string[];
  min?: number;
  max?: number;
  minLength?: number;
  maxLength?: number;
}

function resolve(name: string, prop: JsonSchemaProp, required: boolean): Field {
  let p = prop;
  if (p.anyOf) {
    const nonNull = p.anyOf.find((s) => s.type !== "null");
    if (nonNull) p = { ...prop, ...nonNull, anyOf: undefined };
  }
  const base = { name, label: prop.title ?? name, description: prop.description, required };
  const min = p.minimum ?? p.exclusiveMinimum;
  const max = p.maximum ?? p.exclusiveMaximum;
  if (p.enum) return { ...base, kind: "select", options: p.enum };
  if (p.type === "integer") return { ...base, kind: "integer", min, max };
  if (p.type === "number") return { ...base, kind: "number", min, max };
  if (p.type === "boolean") return { ...base, kind: "checkbox" };
  if (p.type === "string") {
    if (p.format === "date") return { ...base, kind: "date" };
    if ((p.maxLength ?? 0) > 120) return { ...base, kind: "textarea", maxLength: p.maxLength };
    return { ...base, kind: "text", minLength: p.minLength, maxLength: p.maxLength };
  }
  return { ...base, kind: "text" };
}

function hint(f: Field): string {
  const parts: string[] = [];
  if (f.description) parts.push(f.description);
  if (f.kind === "number" || f.kind === "integer") {
    if (f.min !== undefined && f.max !== undefined) parts.push(`range ${f.min} to ${f.max}`);
    else if (f.min !== undefined) parts.push(`at least ${f.min}`);
    else if (f.max !== undefined) parts.push(`at most ${f.max}`);
  } else if (f.kind === "text" && (f.minLength || f.maxLength)) {
    parts.push(`${f.minLength ?? 1}–${f.maxLength} characters`);
  }
  return parts.join(" · ");
}

function validate(f: Field, raw: string | boolean): string | null {
  if (f.kind === "checkbox") return null;
  const value = String(raw ?? "").trim();
  if (!value) return f.required ? "Please fill this in." : null;
  if (f.kind === "number" || f.kind === "integer") {
    const n = Number(value);
    if (Number.isNaN(n)) return "Enter a number.";
    if (f.kind === "integer" && !Number.isInteger(n)) return "Enter a whole number.";
    if (f.min !== undefined && n < f.min) return `Must be at least ${f.min}.`;
    if (f.max !== undefined && n > f.max) return `Must be at most ${f.max}.`;
  }
  if (f.kind === "text") {
    if (f.minLength !== undefined && value.length < f.minLength)
      return `Use at least ${f.minLength} character(s).`;
    if (f.maxLength !== undefined && value.length > f.maxLength)
      return `Use at most ${f.maxLength} character(s).`;
  }
  return null;
}

interface Props {
  schema: JsonSchema;
  fieldOrder: string[];
  initial?: Payload;
  submitLabel: string;
  onSubmit: (payload: Payload) => Promise<void>;
}

export default function SchemaForm({ schema, fieldOrder, initial, submitLabel, onSubmit }: Props) {
  const fields = useMemo(() => {
    const required = new Set(schema.required ?? []);
    return fieldOrder
      .filter((name) => schema.properties[name])
      .map((name) => resolve(name, schema.properties[name], required.has(name)));
  }, [schema, fieldOrder]);

  const [values, setValues] = useState<Record<string, string | boolean>>(() => {
    const v: Record<string, string | boolean> = {};
    for (const f of fields) {
      const init = initial?.[f.name];
      v[f.name] = f.kind === "checkbox" ? Boolean(init) : init === undefined || init === null ? "" : String(init);
    }
    return v;
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set(name: string, value: string | boolean) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    const nextErrors: Record<string, string> = {};
    for (const f of fields) {
      const err = validate(f, values[f.name]);
      if (err) nextErrors[f.name] = err;
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    const payload: Payload = {};
    for (const f of fields) {
      const raw = values[f.name];
      if (f.kind === "checkbox") {
        payload[f.name] = Boolean(raw);
        continue;
      }
      const s = String(raw ?? "").trim();
      if (!s) continue; // omit empty optionals
      payload[f.name] = f.kind === "number" || f.kind === "integer" ? Number(s) : s;
    }

    setBusy(true);
    try {
      await onSubmit(payload);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      {fields.map((f) => (
        <div key={f.name} className={"field" + (errors[f.name] ? " has-error" : "")}>
          <label htmlFor={f.name}>
            {f.label} {!f.required && <span className="req">(optional)</span>}
          </label>

          {f.kind === "select" ? (
            <select
              id={f.name}
              value={String(values[f.name] ?? "")}
              onChange={(e) => set(f.name, e.target.value)}
            >
              <option value="">Choose…</option>
              {f.options?.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          ) : f.kind === "textarea" ? (
            <textarea
              id={f.name}
              value={String(values[f.name] ?? "")}
              onChange={(e) => set(f.name, e.target.value)}
            />
          ) : f.kind === "checkbox" ? (
            <input
              id={f.name}
              type="checkbox"
              checked={Boolean(values[f.name])}
              onChange={(e) => set(f.name, e.target.checked)}
              style={{ alignSelf: "flex-start", width: 20, height: 20 }}
            />
          ) : (
            <input
              id={f.name}
              type={f.kind === "date" ? "date" : f.kind === "text" ? "text" : "number"}
              inputMode={f.kind === "integer" ? "numeric" : undefined}
              step={f.kind === "integer" ? 1 : f.kind === "number" ? "any" : undefined}
              min={f.min}
              max={f.max}
              value={String(values[f.name] ?? "")}
              onChange={(e) => set(f.name, e.target.value)}
            />
          )}

          {hint(f) && <span className="help">{hint(f)}</span>}
          {errors[f.name] && <span className="error-msg">{errors[f.name]}</span>}
        </div>
      ))}

      {formError && <div className="notice">{formError}</div>}

      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "Saving…" : submitLabel}
      </button>
    </form>
  );
}
