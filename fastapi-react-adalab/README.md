# fastapi-react-adalab

A Copier template for AdaLab apps with a FastAPI + SQLModel + SQLite backend and a React + TanStack Router + TanStack Query frontend, served as a single container on port 8000. Ships with three-layer Claude Code guardrails and a Departments/Employees reference data model plus a scaffolded-but-incomplete Projects feature.

Authoritative build spec: [SPEC.md](SPEC.md). If this README and `SPEC.md` disagree, `SPEC.md` wins.

## Stamp the template

This template lives inside the `adamatics/app_coding_templates` monorepo. Stamp it with Copier's `--directory` flag:

```bash
copier copy \
  gh:adamatics/app_coding_templates \
  --directory fastapi-react-adalab \
  <output-path> \
  --trust
```

Copier will prompt for:

- `prospect_name` — human-readable app name (used in `FastAPI(title=...)` and `.adalab/app.json`)
- `app_description` — one-sentence description (used in `.adalab/` config)

`prospect_slug` is derived from `prospect_name` and not prompted.

`--trust` is required because the template runs `_tasks` (`chmod +x` on the guardrail hook and `git init -b main`).

## Re-brand per prospect (in-repo file edits)

Branding is **not** a Copier question. Stamp the template once into a demo repo, then re-brand per prospect by editing two files directly in that repo. The AdaLab Test → Build → Deploy cycle rebuilds the container — that rebuild is an intentional part of the demo narrative.

The two branding files:

1. `frontend/public/logo.svg` — replace with the prospect's logo.
2. `frontend/src/styles/tokens.css` — change the three hex values on `--color-primary`, `--color-secondary`, and `--color-accent` at the top of `:root`.

All frontend components reference `var(--color-*)` tokens, so editing the three hex values propagates site-wide. No other file should carry prospect-specific content.

**Shared-folder overwrite at stamp time.** The `app_template_builder` card, if it finds `~/shared/demo_branding/logo.svg` and `~/shared/demo_branding/tokens.css`, overwrites the stamped-out versions of those two files with the shared copies. Templates must ship Adamatics defaults in both files so stamping without shared-folder overrides still produces a valid, on-brand app.

Reverting after a demo:

```bash
git checkout frontend/public/logo.svg frontend/src/styles/tokens.css
```

## Why `_skip_if_exists`

`copier.yml` lists `frontend/public/logo.svg` and `frontend/src/styles/tokens.css` in `_skip_if_exists`. Running `copier update` later to pull in template improvements will not clobber the per-demo branding edits in those two files.

## What lives where

- `SPEC.md` — authoritative build spec for this template
- `copier.yml` — Copier configuration (three questions, `_skip_if_exists` on branding files)
- `hooks/post_gen.py` — post-generation hook (intentionally minimal; `_tasks` in `copier.yml` handles `chmod` and `git init`)
- `template/` — the files that get stamped into the output repo, with `.jinja` suffixes on rendered files

## Further reading

- [SPEC.md](SPEC.md) — full build specification, data model, guardrail architecture, Definition of Done, and build order
- [../REPO_SPEC.md](../REPO_SPEC.md) — monorepo-level conventions every template must follow
