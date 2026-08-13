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
git clone --branch add-lab-exercise-app-template \
  https://github.com/adamatics/app_coding_templates.git
```

> **Why `--branch`?** The template is still on a review branch and hasn't been merged. Once it
> is, you can drop that line and clone normally.

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

1. **Create a volume** on the AdaLab **Volumes** page (name, size in GB, access control). At
   some institutions only an admin can do this — check early.
2. **Fix its permissions once**, from a lab terminal — a new volume looks fine but every write
   fails until you do:
   ```bash
   cd ~/asv-mnt
   sudo chown root:$NB_GROUP <Volume_Name>
   sudo chmod 775 <Volume_Name>
   ```
   `<Volume_Name>` is the volume's name with spaces replaced by underscores — run
   `ls ~/asv-mnt` to see it.
3. **Open the app in the AdaLab VS Code extension** and run **Test → Build → Deploy**, in that
   order. Skipping Build breaks a first deployment.
4. In the deployment step, mount the volume on the primary container with mount path
   **`lab-data`**, *Read only* **off**, *Fast mount* **on**, and set the environment variables
   `COURSE_PASSWORD` and `ADMIN_PASSWORD`.

The full runbook, including what to do when something goes wrong, is in your app's own
`README.md` under *Persistent storage*.

---

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
