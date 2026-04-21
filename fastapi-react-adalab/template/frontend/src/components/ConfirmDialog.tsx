interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
}

export function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
}: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--color-overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
    >
      <div
        style={{
          background: 'var(--color-bg)',
          padding: 'var(--space-xl)',
          borderRadius: 'var(--radius-md)',
          minWidth: 320,
          maxWidth: 480,
        }}
      >
        <h3>{title}</h3>
        <p>{message}</p>
        <div
          style={{
            display: 'flex',
            gap: 'var(--space-sm)',
            justifyContent: 'flex-end',
            marginTop: 'var(--space-lg)',
          }}
        >
          <button type="button" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className="danger" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
