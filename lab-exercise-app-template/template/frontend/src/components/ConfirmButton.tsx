import { useState } from "react";

// Destructive actions get an explicit confirm step in Charcoal — never a red the palette
// does not contain (§13).
interface Props {
  label: string;
  confirmLabel?: string;
  onConfirm: () => void;
}

export default function ConfirmButton({ label, confirmLabel, onConfirm }: Props) {
  const [armed, setArmed] = useState(false);
  if (!armed) {
    return (
      <button type="button" className="btn btn-danger btn-small" onClick={() => setArmed(true)}>
        {label}
      </button>
    );
  }
  return (
    <span className="row">
      <span className="muted">{confirmLabel ?? "Are you sure?"}</span>
      <button
        type="button"
        className="btn btn-danger btn-small"
        onClick={() => {
          setArmed(false);
          onConfirm();
        }}
      >
        Confirm
      </button>
      <button type="button" className="btn btn-secondary btn-small" onClick={() => setArmed(false)}>
        Cancel
      </button>
    </span>
  );
}
