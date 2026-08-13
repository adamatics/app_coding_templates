# Deploying this app on AdaLab

What an agent (or a teacher) needs to know to get this specific app deployed and keep it
working. Written for this template — the platform's own app-builder guidance is the general
authority if you need more.

## `.adalab/` is deployment state, not scratch

Treat it like a lockfile: source-controlled, hand-editable, never invented. Some fields are
**managed by the deploy flow** and must ship as `null` from the template — `app_id`,
`metadata_id`, `image_version.current_image_version`. If a deploy populates them, **commit the
result**; otherwise the next session re-derives stale state.

`tests/test_adalab_config.py` enforces the rules below. Run the test suite before deploying —
every one of these failures otherwise surfaces at build or deploy time, often in front of a class.

## The rules that bite

**Container filenames.** `local_container_<uid>.json` where the suffix is an **integer equal to
the `uid` field inside**. Naming the file after the image (`local_container_myapp.json`) is the
documented cause of duplicate-container deploys. `uid` is a number, never a string. `uid`s and
`container_image_name`s must be unique across all container files.

**Exactly one `primary_container: true`** — the browser-facing one. The API rejects anything else.

**`app_url`** must match `^[a-z0-9]([-a-z0-9]*[a-z0-9])?$`, be ≤ 63 characters, and is
**globally unique on the tenant**. Check availability before deploying; a URL freed by a
deleted app may not be released immediately. This app uses the project slug.

**Reserved environment variables:** `_UA_CLIENT_ID`, `_UA_CLIENT_SECRET`, `_NAMESPACE` are
injected by the platform — including them in `environment_variables` fails the deploy.

**Never commit secrets.** `COURSE_PASSWORD` and `ADMIN_PASSWORD` are set in the App Deployment
wizard, not in `.adalab/`. Anyone who can read the repo can read the manifest.

**Resources.** CPU cap 2 cores, RAM cap 2000 MB. The scaffold default of 500 MB is too tight
for Streamlit + pandas + plotly + PDF rendering; this app ships `max_ram: 1500`.

## The URL prefix (the app serves at the root)

AdaLab serves apps at `/apps/<app_url>/`. There are exactly two valid setups and they must
never be mixed:

| Setup | `stripped_prefix` | App | Verdict |
| --- | --- | --- | --- |
| Proxy strips the prefix, app at the root | `true` (default) | no `--server.baseUrlPath` | **What this app uses** |
| Proxy forwards the prefix, app is prefix-aware | `false` | `--server.baseUrlPath=apps/<url>` | Escape hatch only |

The root setup works because Streamlit emits **relative** asset URLs (`./static/…`,
`./_stcore/stream`): the browser resolves them against the prefixed page and the proxy strips
them again inbound. Page, assets and WebSocket all verified.

It is also the only setup compatible with the extension's **Test** step, which probes `/` on
the container and expects a 2xx. With `--server.baseUrlPath` set, `/` is a 404 and Test fails
with `CONTAINER_READINESS_FAILED: Unexpected status code: 404`.

`tests/test_adalab_config.py` asserts the two settings stay consistent in both directions.

## Persistence: the Shared Volume (ASV)

Container filesystems are wiped on every redeploy. An ASV is the only correct place for
student data, and this app **refuses to start** without one.

**The volume is a separate resource.** It is not created by the VS Code extension, not by
`.adalab/`, and not by deploying. Someone creates it on the **Volumes page** first. If a user
asks why the app won't start, this is almost always the answer — walk them through the four
steps below rather than suggesting they change `DATA_DIR`.

### 1. Create it (Volumes page)

Two-step wizard: *Information* (name, description, **size in GB — fixed at creation**, only
resizable by someone with Edit rights) and *Access control* (**View / Mount / Edit**,
hierarchical: Edit ⊃ Mount ⊃ View; each settable to Public / Logged in / Userlist / Groups).
Mount rights are needed to attach it to an app.

**At some institutions only an admin can create volumes.** Surface that early — it is a
scheduling problem, not a technical one.

### 2. The one-time chmod (the single most common failure)

A new volume has ACL access but no filesystem permissions: the ACL is green, the mount
succeeds, and every write still raises `PermissionError`.

Note there are **two distinct mount actions**, each with its own mount path, and they do not
have to match:

| | Where | Mount path | Result |
| --- | --- | --- | --- |
| **Lab** | burger menu → Volumes → **Mount** | pre-filled with the volume name, spaces as underscores (e.g. `CPDSE_Course_App_Data`) | `~/asv-mnt/<that>` — for browsing and the chmod. "Mount from root" checked gives `/asv-mnt/<that>` instead; "Read only" must be unchecked to chmod. |
| **App** | App Deployment wizard → Volume mounts | whatever the app expects — `lab-data` for this template | `/asv-mnt/lab-data`, matching `DATA_DIR` |

Doing one does not do the other. If a user says "I mounted it", ask which — and if writes
fail, check the app's mount path matches `DATA_DIR`, not the lab's.

Attach it to a lab first, then run once per volume from a lab terminal:

```bash
cd ~/asv-mnt
sudo chown root:$NB_GROUP <Volume_Name>
sudo chmod 775 <Volume_Name>
```

`$NB_GROUP` is `adalab-users` on most installations.

**Do not misread the output.** `sudo: unable to send audit message: Operation not permitted`
is sudo failing to reach the audit log inside a container — the command still runs. And a
subsequent bare `chmod` returning `Operation not permitted` means the `chown` *succeeded*
(root owns it now). Diagnose from the result, not the noise:

```bash
ls -ld ~/asv-mnt/<Volume_Name>    # want: drwxrwsr-x root adalab-users
```

Group must be `adalab-users` (or whatever `$NB_GROUP` holds) with group write. If it shows
`root root`, `$NB_GROUP` was empty — re-run naming the group explicitly. **`<Volume_Name>` is the volume's name
with spaces replaced by underscores** — `CPDSE Lab Data` → `CPDSE_Lab_Data`; tell the user to
`ls ~/asv-mnt` rather than guess. A lab set to "Mount from Root" sees `/asv-mnt/...` instead.
A newly attached volume can take ~2 minutes to appear in a running lab.

Expected to become implicit in AdaLab v1.6 (~mid-2026); mandatory until the platform is upgraded.

### 3. Mount it (App Deployment wizard)

One row under **Volume mounts** on the **primary container**, four controls: *Volume*,
*Mount path*, *Read only*, *Fast mount*.

- **`mount_path` is the part after `/asv-mnt/`** — no leading slash (it doubles), no trailing
  slash (rejected outright). This app expects `lab-data`, matching `DATA_DIR=/asv-mnt/lab-data`.
  A test keeps those two aligned; if you change one, change the other.
  The mount path is independent of the volume's *name* — the name only decides the directory
  name inside a lab.
- **Read only: off.** The app writes.
- **Fast Mount: on.** Required here, not an optimisation — SQLite over a network mount is slow
  and can corrupt under load. At most **one Fast Mount per app**, and it is a property of the
  attachment, so the same volume can be Fast-Mounted here and network-mounted elsewhere.

After deploy, a mount can be changed in place from the app's kebab menu → **Edit Mount**.

### 4. Sharing across the course's apps

One ASV can be mounted into many apps and labs simultaneously — that is how a KUID's history
stays reachable across a course. Each app writes to its own subdirectory (named after its
slug). Use the **same mount path** in every app; a volume cannot be mounted twice on the *same*
container.

### Things that will bite

- **`lost+found` and `.AVI_SUCCESS`** appear in every mounted volume. Use
  `core.storage.list_volume_dir`, never a raw `iterdir`.
- **Never put secrets on the volume** — anyone with Mount rights can read them. Passwords are
  environment variables set in the deploy wizard.
- **Size is fixed at creation.** Uploaded documents and years of results accumulate; the event
  log rotates but the rest does not.
- **Single writer.** SQLite + WAL means one replica. Never scale this app horizontally.

This app deliberately does **not** create `DATA_DIR` if it is missing, unlike the generic
platform pattern which does `mkdir(parents=True)` first. On an unmounted path that silently
creates a container-local directory — exactly the "looks fine in class, loses a year of data on
redeploy" failure this template exists to prevent. `core/preflight.py` fails loud instead.

## Order of operations

**Test → Build → Deploy.** Skipping Build breaks a first-time Deploy. Set `COURSE_PASSWORD`,
`ADMIN_PASSWORD` and the volume mount in the wizard at deploy time.

## When something is wrong

| Symptom | Likely cause |
| --- | --- |
| Assets 404, page never finishes loading | `stripped_prefix` / `baseUrlPath` mismatch |
| `PermissionError` on first write | New volume without the one-time chmod |
| Data gone after redeploy | No volume mounted, or mounted on the wrong container |
| Deploy rejected: image already exists | Tag already pushed — bump `next_image_version` |
| Deploy rejected: more than one primary | Two container files with `primary_container: true` |
| App slow / DB stalls | Volume mounted without Fast Mount |
| Startup aborts naming `DATA_DIR` | Working as designed — mount the volume |
