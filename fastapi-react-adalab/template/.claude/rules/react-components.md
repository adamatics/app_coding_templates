---
paths: ["frontend/src/**"]
---
# React component rules

- No hex literals anywhere under `frontend/src/` except `styles/tokens.css`. Use `var(--color-primary)`, `var(--color-secondary)`, `var(--color-accent)`.
- Every new page under `src/routes/xs/` uses `DataTable`, `FormField`, `ConfirmDialog` from `components/`.
- Every data fetch uses TanStack Query hooks defined in `src/api/x.ts`.
- Every form uses React Hook Form + Zod.
- Never import from `frontend/src/lib/basepath.ts`, `frontend/src/api/client.ts`, or `frontend/src/main.tsx` except in files that already do.
