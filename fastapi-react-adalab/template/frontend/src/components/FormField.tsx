import type { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  error?: string;
  children: ReactNode;
}

export function FormField({ label, htmlFor, error, children }: FormFieldProps) {
  return (
    <label
      htmlFor={htmlFor}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-xs)',
        marginBottom: 'var(--space-md)',
      }}
    >
      <span style={{ fontWeight: 600 }}>{label}</span>
      {children}
      {error && (
        <span
          style={{
            color: 'var(--color-danger)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          {error}
        </span>
      )}
    </label>
  );
}
