# React / frontend conventions

You should rarely be here — the frontend is chassis and derives everything from the schema.
If you are reading this because a task seems to need a frontend change, re-check whether a
schema change in `exercise/schema.py` achieves it instead.

If you genuinely must work in the frontend (a chassis/template change):

- **React 18 + Vite + TypeScript**, function components with hooks, `strict` TypeScript.
- **Colour comes only from `frontend/src/theme.css`** (CSS variables). No hex anywhere else —
  `npm run check:theme` fails the build on a violation. Only the six approved CPDSE fill/ink
  pairs; the palette has no red/amber, so convey state with words and weight, not colour.
- **Verdana** with the declared fallback stack; weights 400/700 only; no italics in headings.
- The measurement form/table/chart/export are generated from the JSON Schema (`SchemaForm`,
  `DataTable`, `Chart`). Extend those generically, never per-exercise.
- Base path is resolved at runtime from the URL in `src/lib/basepath.ts`; API calls and the
  router basename use it. Don't hardcode `/apps/...` or reintroduce a build-time base env.
- Formatting is **prettier** (a PostToolUse hook runs it if installed).
