# adamatics/app_coding_templates

A curated set of [Copier](https://copier.readthedocs.io/) templates for AdaLab apps. Each
template is a self-contained subdirectory (see `REPO_SPEC.md` for shared conventions).

## Templates

| Template | Status | What it is |
| --- | --- | --- |
| [`lab-exercise-app-template`](lab-exercise-app-template/) | Built | CPDSE student lab-exercise apps: student groups record measurements; append-only, cohort-based data persists across years. FastAPI + SQLite + React, one container. **Fixed** CPDSE identity (not per-prospect). |
| [`fastapi-react-adalab`](fastapi-react-adalab/) | Spec only | Reference FastAPI + React demo template (per-prospect branding). See its `SPEC.md`. |

## Stamp a template

Copier has no monorepo-subdir flag (that is a cookiecutter feature), so clone the repo and
point Copier at the template's subdirectory:

```bash
git clone git@github.com:adamatics/app_coding_templates.git
copier copy app_coding_templates/<template-name> <output-path> --trust
```

For example, `copier copy app_coding_templates/lab-exercise-app-template ./my-exercise --trust`.
See each template's `README.md` for its questions and its `SPEC.md` for the authoritative
build spec. (`REPO_SPEC.md` documents a `--directory` form; that flag does not exist in
Copier ≥ 9 — see the lab-exercise-app-template SPEC divergences.)
