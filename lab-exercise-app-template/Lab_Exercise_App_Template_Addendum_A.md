# ADDENDUM A: AdaLab conventions and persistence

*Companion to `Lab_Exercise_App_Template_Spec.md`. Apply on top of the work already in progress. Where this addendum conflicts with the base spec, this addendum wins.*

This closes the one open item flagged in base spec §12: persistence depends on a mounted volume that survives redeploys. It does, via an AdaLab Shared Volume (ASV), and the mechanics are documented below. It also aligns the template with the conventions already proven in the `fastapi-react-adalab` template so this becomes a sibling in the same family rather than a one-off.

---

## A1. Load-bearing AdaLab constraints

Deviation breaks deployment. These override any conflicting choice in the base spec.

- **Single container.** Frontend builds to static assets; FastAPI serves them alongside the API. No nginx, no second process.
- **File named `Containerfile`**, never `Dockerfile`.
- **Port 8000** everywhere: `port`, `test_serving_port`, and uvicorn's `--port`. **This supersedes the base spec's port 8080 and the `app_port` Copier question, which is removed.**
- **Vite `base: './'`** so asset references are relative.
- **Router basepath resolved at runtime** from `window.location.pathname`, in a dedicated `frontend/src/lib/basepath.ts`. This replaces the base spec's `BASE_PATH` env var approach: AdaLab serves apps under a prefix that the app discovers at runtime, so a build-time env var is the wrong mechanism.
- **`.adalab/app.json` must set `stripped_prefix: true`.**
- **`.adalab/local_container_*.json` must set `uid: 1`** (non-null placeholder; AdaLab overwrites it on Build).
- **`.vscode/settings.json` contains `{"adalab.workingMode": "appBuilder"}`.**
- **Deployment order is Test → Build → Deploy.** Skipping Build breaks first-time Deploy. State this in the app README.
- **Python 3.11** in the container (matches AdaLab's `python:3.11-slim`). Supersedes the base spec's 3.12.

## A2. The `.adalab/` folder

Three files, mirroring the sibling template.

**`.adalab/project.json`** (verbatim, not templated):

```json
{"type": "appBuilder"}
```

**`.adalab/app.json.jinja`:**

```json
{
    "app_id": null,
    "app_name": "{{ exercise_title }}",
    "app_description": "{{ app_description }}",
    "app_url": "{{ project_slug }}",
    "stripped_prefix": true,
    "access_level": "logged_in",
    "acl_userlist": [],
    "acl_group_names": [],
    "idp_enabled": false,
    "idp_scope": null,
    "maintainers": []
}
```

`access_level` note for this use case: students are not AdaLab users, so a deployment intended for a class will likely need `public`. Ship `logged_in` as the safe default and document the change in the app README as a deliberate teacher decision, not a template default. Whoever deploys decides, and the choice is visible in a versioned file.

**`.adalab/local_container_demo.json.jinja`:**

```json
{
    "uid": 1,
    "container_image_name": "{{ project_slug }}",
    "image_version": {
        "current_image_version": null,
        "next_image_version": "0.1.0"
    },
    "container_description": "{{ app_description }}",
    "container_file": "./Containerfile",
    "build_context": "./",
    "metadata_id": null,
    "primary_container": true,
    "port": 8000,
    "test_serving_port": 8000,
    "max_cpu": 1,
    "min_cpu": 0,
    "max_ram": 500,
    "min_ram": 20,
    "command": null,
    "environment_variables": [],
    "is_locked": false,
    "volume_mounts": []
}
```

`volume_mounts` stays empty in the template. Mounts are configured in the App Deployment wizard at deploy time, not declared in the repo (see A3).

`.adalab/card.json` from base spec §12 remains, unchanged.

## A3. Persistence via an AdaLab Shared Volume

**The model.** A container's filesystem is wiped on every redeploy. An ASV is a first-class persistent resource created on the Volumes page and attached to apps and labs. It is not declared inline in the repo; the container config references an existing volume, and the mount is configured in the App Deployment wizard.

**Path contract.** A volume mounted into an app always lands at `/asv-mnt/<mount-path>`. You specify only the `<mount-path>` part, it is required, and it must not end with a slash. For this template the convention is mount path `lab-data`, giving `/asv-mnt/lab-data`.

**`DATA_DIR` default changes to `/asv-mnt/lab-data`** (was `/data`), still overridable by env var so local development works unchanged.

**Fast Mount: turn it on.** SQLite over a network mount is the wrong shape for anything with real write traffic. One Fast Mount is permitted per deployed app; this app is single-container, so it takes it. Document it as a required deployment setting, not an optimization.

**Every ASV needs a one-time chmod before any app can write to it.** A fresh volume has no filesystem permissions; the ACL can be correct, the mount can succeed, the UI can show green, and every write still fails with `PermissionError`. From a lab terminal with the volume mounted:

```bash
sudo chown root:$NB_GROUP <Volume_Name>
sudo chmod 775 <Volume_Name>
```

Note that this is a separate layer from the volume ACL (View / Mount / Edit), which governs who may attach the volume at all. Both layers must be set: correct ACL without chmod means writes fail; correct chmod without ACL means you cannot mount. This step is expected to become implicit in AdaLab v1.6; until the target platform is upgraded, treat it as mandatory. Put the full runbook in the app README: create volume → set ACL → mount in a lab → chown and chmod → mount in the app with Fast Mount on.

**Two files appear in every mounted volume and must be ignored in code**: `lost+found` and `.AVI_SUCCESS`. Any directory listing or export logic must filter them.

**Defensive IO is mandatory.** The volume may be absent in local development, the path may not exist on first run, the disk may be full. On startup, probe writability and, if the probe fails, refuse to start with an explicit message naming `DATA_DIR` and pointing at the volume mount configuration. Silent fallback to container-local storage is forbidden: it would produce an app that appears to work and loses a year of student data at the next redeploy. All writes to the volume outside SQLite use write-temp-then-`replace()` for atomicity.

SQLite lives at `$DATA_DIR/results.sqlite` with WAL mode, which fits the documented "small embedded database, single-instance app" pattern. This constrains the app to a single replica; state that explicitly in the README so nobody scales it horizontally and corrupts the database.

## A4. Alignment with the sibling template

Adopt these conventions from `fastapi-react-adalab` so the two templates are recognisably one family.

**Guardrails in three layers**, replacing the single hook in base spec §11:

1. `CLAUDE.md` states intent and names the protected zones.
2. `.claude/settings.json` `permissions.deny` blocks edits to chassis paths, with `permissions.ask` on sensitive-but-editable files (`theme.css`, `.adalab/local_container_demo.json`, dependency-add commands).
3. `.claude/hooks/chassis_guard.py` is the actual enforcement, a PreToolUse hook exiting 2 to block and feed guidance back to the agent. Deny rules are best-effort; the hook is real. Model it on `protect_paths.py`, including the dangerous-bash blocks.

**Protected path list** for this template: `backend/app/core/**`, `backend/app/main.py`, `backend/app/db.py`, `backend/app/models.py`, `backend/app/auth.py`, `frontend/src/lib/basepath.ts`, `frontend/src/App.tsx`, `frontend/src/components/**`, `frontend/vite.config.ts`, lockfiles, `.adalab/app.json`, `.adalab/project.json`, `.vscode/**`, `Containerfile`, `.claude/hooks/**`, `.claude/settings.json`, secrets. Deliberately **not** protected: everything under `exercise/`, which is the seam.

**Also adopt:** a `PostToolUse` formatting hook (ruff plus prettier), a `SessionStart` message announcing that guardrails are active, `.claude/rules/*.md` for python style and React component conventions, `_skip_if_exists` in `copier.yml` on `frontend/src/theme.css` so a `copier update` never overwrites identity edits, and `_tasks` for `chmod +x` on hooks plus `git init -b main`.

**Containerfile shape** (two-stage, mirroring the sibling): Node 20 stage builds the frontend, `python:3.11-slim` stage installs requirements and copies `dist` into `./static`, `EXPOSE 8000`, uvicorn on port 8000.

## A5. Changes to the base spec, consolidated

| Base spec | Replaced by |
|---|---|
| Port 8080 and `app_port` Copier question | Port 8000 fixed, question removed (A1) |
| `BASE_PATH` env var | Runtime basepath resolution in `frontend/src/lib/basepath.ts` (A1) |
| Python 3.12 | Python 3.11 (A1) |
| `DATA_DIR` default `/data` | `/asv-mnt/lab-data` (A3) |
| Single guardrail hook | Three-layer guardrails (A4) |
| "Open deployment question" on volume persistence | Resolved: ASV with Fast Mount, chmod runbook in README (A3) |

Environment variable set becomes: `DATA_DIR` (default `/asv-mnt/lab-data`), `ADMIN_PASSWORD` (required for admin, fail closed when unset), `DEMO_MODE` (default `false`).

## A6. Additional acceptance criteria

Append to base spec §15:

11. App builds and runs on port 8000 with `.adalab/` files matching A2 exactly, including `stripped_prefix: true` and `uid: 1`.
12. Startup with an unwritable or missing `DATA_DIR` fails loudly with a message naming the path and the volume-mount fix; it does not silently fall back to container-local storage.
13. `lost+found` and `.AVI_SUCCESS` are filtered everywhere the app enumerates volume contents.
14. Redeploy simulation: run the container with a host directory mounted at `/asv-mnt/lab-data`, submit results, destroy the container, rebuild with a new image tag, run again against the same mount. All cohorts, groups, and results intact.
15. Router basepath resolves at runtime: serving the app under a path prefix leaves navigation, API calls, and admin login working with no rebuild.
16. All three guardrail layers present and consistent: the deny list, the hook's protected paths, and CLAUDE.md name the same files.
17. The app README contains the ASV runbook (create, ACL, mount in lab, chown/chmod, mount in app with Fast Mount) and states the single-replica constraint.
