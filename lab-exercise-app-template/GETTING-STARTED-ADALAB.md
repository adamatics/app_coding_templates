# Getting started in AdaLab

How to make your own copy of a lab-exercise app from the template, using the terminal in an
AdaLab lab. No GitHub account or credentials needed — the template repository is public.

Copy-paste each block in order. Every step ends with something you can check, so you know
whether it worked before moving on.

---

## Before you start

Open a **lab** in AdaLab and open a **terminal** in it (in JupyterLab: *File → New → Terminal*).
Everything below happens in that terminal, in your lab's home directory.

Check you have what you need:

```bash
python3 --version     # need 3.10 or newer
git --version
```

Both are normally present in an AdaLab lab. If `python3` reports 3.9 or older, tell Sune —
Copier needs 3.10+ and we'll find you another route.

---

## 1. Install Copier

Copier is the tool that stamps out a new app from the template.

```bash
pip install --user copier
```

Then check it's on your PATH:

```bash
copier --version
```

If that says `command not found`, your user-install directory isn't on the PATH. Fix it for
this session and future ones:

```bash
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
copier --version
```

You should see `copier 9.x`.

---

## 2. Get the template

```bash
cd ~
git clone https://github.com/adamatics/app_coding_templates.git
```

Check it arrived:

```bash
ls app_coding_templates/lab-exercise-app-template
```

You should see `copier.yml`, `README.md`, `SPEC.md` and a `template/` folder.

---

## 3. Stamp your own app

Copier asks a short list of questions and writes a complete app into a new folder.

```bash
cd ~
copier copy app_coding_templates/lab-exercise-app-template my-exercise --trust
```

`--trust` is required: it lets the template make its hooks executable and run `git init` in
your new app. You can read exactly what it runs in `copier.yml` under `_tasks`.

You'll be asked for:

| Question | What it means | Example |
| --- | --- | --- |
| `project_name` | Human-readable name | `Titration Lab` |
| `project_slug` | Folder name **and the app's URL** on AdaLab (`/apps/<slug>/`). Lowercase letters, digits, hyphens; must be unique across the whole AdaLab installation. | `titration-lab` |
| `exercise_title` | Shown in the app header and on the Gallery card | `Acid–base titration` |
| `course_code` | Your course code | `FARM-2026` |
| `app_description` | One line, used on the card | *(a sensible default is offered)* |
| `adalab_author` | Your AdaLab user ID — press Enter to fill it automatically | *(leave blank)* |
| `host_institution` | `SDU`, `UCPH` or `CPDSE` — footer text only | `UCPH` |
| `contact_email` | Who students should contact | `you@ku.dk` |
| `default_cohort_label` | The first year/cohort | `2026-fall` |

To accept every default without being asked, add `--defaults`.

Check what you got:

```bash
cd ~/my-exercise
ls
```

---

## 4. Check it works

Install the dependencies and run the test suite:

```bash
cd ~/my-exercise
pip install --user -e ".[dev]"
DATA_DIR=$(mktemp -d) python3 -m pytest -q
```

You should see roughly **138 passed**. That covers the whole app, including the checks that
matter most — data is never lost, 60 students can submit at once, and the `.adalab/`
deployment config is valid.

If tests fail here, before you've changed anything, that's a bug in the template — please tell
Sune rather than working around it.

---

## 5. Make it your exercise

Only four files describe your exercise. Everything else is shared machinery you never touch
(and a guard will stop you editing by accident).

```bash
cd ~/my-exercise/exercise
ls
```

| File | What you change |
| --- | --- |
| `schema.py` | The values a student records — name, type, unit, allowed range |
| `capture.py` | The data-entry form students fill in at the bench |
| `analysis.py` | The plots shown afterwards |
| `content.md` | The instructions and the questions students answer |

**Read the top of `capture.py` and `analysis.py` first** — each begins with an explanation of
what the file is for, what it must return, and how to write a good one.

The app ships with a worked logP example so it runs end to end before you change anything.
Replace it with your own exercise.

After each change, re-run the tests:

```bash
cd ~/my-exercise
DATA_DIR=$(mktemp -d) python3 -m pytest -q
```

Working with Claude Code in this folder? Just describe the change — *"add a pH field, range 0
to 14"* — and it will edit the right file. The repository tells the agent where the boundaries
are.

---

## 6. Deploy it (when you're ready)

The app stores everything on an **AdaLab Shared Volume**, and **it will refuse to start
without one** — that is deliberate, so a redeploy can never silently wipe a year of student
results.

### The CPDSE volume

You do **not** need to create a volume. One already exists for all CPDSE course apps:

| | |
| --- | --- |
| **Name** | `CPDSE Course App Data` |
| **Volume ID** | `6` |
| **Size** | 20 GB (fixed at creation) |
| **Owner** | `sune` |
| **Mount path to use** | `lab-data` |

**Every CPDSE lab-exercise app mounts this same volume.** Each app writes into its own
subdirectory named after its slug, so they never collide:

```
/asv-mnt/lab-data/
├── titration-lab/      results.sqlite · results.csv · events.jsonl · documents/ · exports/
├── logp-lab/           …
└── spectroscopy-lab/   …
```

That is also what makes a student's history reachable across the course's apps — one volume,
many apps, one place to look.

### Mount it in the App Deployment wizard

On the **primary container**, add one row under **Volume mounts**:

| Control | Value |
| --- | --- |
| **Volume** | `CPDSE Course App Data (20 GB)` |
| **Mount path** | `lab-data` — the part *after* `/asv-mnt/`. No leading slash, no trailing slash (a trailing slash is rejected). |
| **Read only** | **off** — the app must write |
| **Fast mount** | **on** |

Fast Mount is required, not optional: SQLite over a plain network mount is slow and can
corrupt under load. It is a property of *this app's attachment*, so every course app can Fast
Mount the same volume independently.

Also set the environment variables in the wizard — **never in `.adalab/`**:

| Variable | Value |
| --- | --- |
| `COURSE_PASSWORD` | the password you give the class, rotated each semester |
| `ADMIN_PASSWORD` | your admin password for the Admin page |

If you or an agent edits `.adalab/local_container_1.json` by hand instead, the row is:

```json
"volume_mounts": [
  {"volume_id": 6, "mount_path": "lab-data", "read_only": false, "direct": true}
]
```

### Working with the volume yourself (browsing it, or fixing permissions)

There are **two different "mount" actions**, and mixing them up is the usual source of
confusion:

| Where | What it does | When you use it |
| --- | --- | --- |
| **Volumes page → Mount** | Attaches the volume to **your lab**, so it appears at `~/asv-mnt/…` and you can browse or fix it from a terminal | Inspecting the data, taking a copy, the one-time `chmod` |
| **App Deployment wizard → Volume mounts** | Attaches the volume to **the deployed app** | Every app you deploy (see above) |

Doing one does not do the other.

To attach it to your lab: open the **burger menu → Volumes**, find **CPDSE Course App Data**,
and click **Mount**. A *Mount information* dialog appears — for the one-time `chmod`, and for
browsing, take the defaults:

| Field | Value | Why |
| --- | --- | --- |
| **Mount path** | `CPDSE_Course_App_Data` (pre-filled) | This is the **directory name inside your lab**, nothing more. It is pre-filled from the volume name with spaces turned into underscores. Whatever you type here is what you must use in the `chmod` below, so keep the default. |
| **Mount from root** | **unchecked** | Unchecked puts it at `~/asv-mnt/…` (`/home/<you>/asv-mnt/…`), which is what the commands below assume. Checked would put it at `/asv-mnt/…`. |
| **Read only** | **unchecked** | Must be unchecked, or the `chmod` — and any repair you came to do — will fail. |

The dialog shows you the result: *Volume will be mounted at
`/home/<you>/asv-mnt/CPDSE_Course_App_Data`*.

> **This lab mount path is unrelated to the app's mount path.** In your lab the volume is
> `CPDSE_Course_App_Data`; in a deployed app you mount the same volume at `lab-data`, giving
> `/asv-mnt/lab-data`. They are two independent settings on the same volume, and they do not
> need to match.

A newly attached volume can take ~2 minutes to show up in a running lab; wait, or restart the lab.

From there you can browse every app's data:

```bash
ls ~/asv-mnt/CPDSE_Course_App_Data          # one subdirectory per app
ls ~/asv-mnt/CPDSE_Course_App_Data/titration-lab
```

(`lost+found` and `.AVI_SUCCESS` are platform artifacts, not yours — ignore them.)

### One-time: fix the volume's filesystem permissions

A brand-new volume has ACL access but **no filesystem permissions**: the mount succeeds, the
wizard looks happy, and every write still fails with `PermissionError`.

It needs doing **once, ever, by one person** — not by each teacher. With the volume mounted in
your lab as above, run in a lab terminal:

```bash
cd ~/asv-mnt
sudo chown root:$NB_GROUP CPDSE_Course_App_Data
sudo chmod 775 CPDSE_Course_App_Data
```

`$NB_GROUP` resolves to `adalab-users` on most installations.

**Ignore `sudo: unable to send audit message: Operation not permitted`.** It appears twice and
looks like a failure, but it is only sudo complaining that it cannot reach the audit log inside
a container — the command itself runs. Likewise, if you then try `chmod` *without* `sudo` and
get `Operation not permitted`, that is expected: root now owns the directory, which means the
`chown` worked.

Confirm it took:

```bash
ls -ld ~/asv-mnt/CPDSE_Course_App_Data
touch ~/asv-mnt/CPDSE_Course_App_Data/.probe && rm ~/asv-mnt/CPDSE_Course_App_Data/.probe && echo WRITABLE
```

You want to see the group **`adalab-users`** with group write, e.g.:

```
drwxrwsr-x 2 root adalab-users 4096 ... CPDSE_Course_App_Data
      ^^^ group rwx (the s is setgid — new files inherit the group, which is what you want
          on a volume shared by several apps)
```

If the group shows as `root` rather than `adalab-users`, `$NB_GROUP` was empty when you ran
the command. Name the group explicitly and re-run:

```bash
sudo chown root:adalab-users ~/asv-mnt/CPDSE_Course_App_Data
sudo chmod 775 ~/asv-mnt/CPDSE_Course_App_Data
```

*(AdaLab 1.6 is expected to make this implicit, and this instance already reports 1.6.0 — so
try a deploy first and only run the chmod if writes fail.)*

### Deploy

Use the AdaLab VS Code extension in this order: **Test → Build → Deploy**. Skipping Build
breaks a first-time deploy.

**Test needs no volume.** With no volume and no `COURSE_PASSWORD`, the app starts in
**preview mode** on scratch space and says so on every screen — that is how you check it
renders. Nothing can be collected in that state, because students cannot sign in without the
course password.

### Verify

Open the deployed app, sign in with the course password, register as a test student, submit
one result, then redeploy and check it is still there. Take a backup from
**Admin → Export → Download database** before your first real class.

## If you get stuck

| Symptom | Likely cause |
| --- | --- |
| `copier: command not found` | `~/.local/bin` not on PATH — see step 1 |
| `copier copy` complains about `_tasks` | You left out `--trust` |
| Tests fail before you changed anything | Template bug — please report it |
| App won't start, message mentions `DATA_DIR` | No volume mounted — that's the guard working |
| Every write fails with `PermissionError` | The volume needs its one-time `chmod` (step 6.2) |
| Deploy rejected: app URL taken | `project_slug` must be unique across the whole installation |

Anything else, send the terminal output to [Sune] — the error messages are written to say what
to do next.
