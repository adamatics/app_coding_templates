# adamatics/app_coding_templates

A curated set of [Copier](https://copier.readthedocs.io/) templates for AdaLab apps. Each
template is a self-contained subdirectory (see `REPO_SPEC.md` for shared conventions).

## Templates

| Template | Status | Stack | What it is |
| --- | --- | --- | --- |
| [`lab-exercise-app-template`](lab-exercise-app-template/) | Built | **Streamlit** + SQLite, one container | CPDSE student lab-exercise apps. Student groups record measurements behind a course-password gate; append-only, cohort-based data persists across years for comparison. **Fixed** CPDSE identity (not per-prospect branding). |
| [`fastapi-react-adalab`](fastapi-react-adalab/) | Spec only | FastAPI + React | Reference demo template with per-prospect branding. See its `SPEC.md`. |

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

## What every template here gets right about AdaLab

These are the conventions that make a stamped app deploy first time. They are enforced by
tests in `lab-exercise-app-template`, and worth copying into any new template:

- **`Containerfile`** (not `Dockerfile`), single container, **port 8000**, `python:3.11-slim`.
- **`.adalab/` is deployment state**, source-controlled and hand-editable: `project.json`,
  `app.json`, and one `local_container_<uid>.json` per container. The filename's integer
  suffix **must equal the `uid` field inside** — naming a file after the image is the usual
  cause of duplicate-container deploys. Exactly one container is `primary_container: true`.
- **`app_id`, `metadata_id` and `current_image_version` ship as `null`** and are filled in by
  the deploy flow. Commit them afterwards, or the next deploy re-derives stale state.
- **`app_url`** matches `^[a-z0-9]([-a-z0-9]*[a-z0-9])?$`, ≤ 63 chars, and is globally unique
  on the tenant.
- **The URL prefix is all-or-nothing.** An app is either prefix-aware with
  `stripped_prefix: false`, or serves at the root with `stripped_prefix: true` — never mixed,
  or static assets 404 and websockets fail to connect.
- **Persistence means an AdaLab Shared Volume (ASV)** — and the volume is a **separate resource
  the app developer must create**, not something deploying or the VS Code extension does for
  them. This is the most common reason a first deployment doesn't work, so document it in every
  template:
  - Created on the **Volumes page**: name, description, **size in GB fixed at creation**, then
    access control (**View / Mount / Edit**, hierarchical). At some institutions only an admin
    can create volumes.
  - **A new volume needs a one-time `chmod`** from a lab terminal
    (`cd ~/asv-mnt; sudo chown root:$NB_GROUP <Volume_Name>; sudo chmod 775 <Volume_Name>`) or
    every write fails with `PermissionError` while the UI shows green. `<Volume_Name>` is the
    volume name **with spaces replaced by underscores**. Implicit from AdaLab v1.6.
  - **`mount_path` is the part *after* `/asv-mnt/`** — no leading slash, no trailing slash — and
    it must match whatever path the app reads (`DATA_DIR` or equivalent).
  - **Fast Mount** removes the network hop; required for databases and other IO-heavy work.
    One per app, and it is a property of the attachment, not the volume.
  - One ASV can be mounted into **many apps and labs at once**; a volume cannot be mounted twice
    on the same container. `lost+found` and `.AVI_SUCCESS` appear in every mount — filter them.
- **Never commit secrets** to `.adalab/`; set them as environment variables at deploy time.
  `_UA_CLIENT_ID`, `_UA_CLIENT_SECRET` and `_NAMESPACE` are reserved by the platform.
- **Deploy order is Test → Build → Deploy.** Skipping Build breaks a first-time deploy.

For the full platform guidance, use the `adalab-app-builder` plugin skills; the summary above
is only what these templates depend on.
