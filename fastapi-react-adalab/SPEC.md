# AdaLab Demo Template: Build Specification (v3)

Single source of truth for building the `fastapi-react-adalab` template within the `adamatics/app_coding_templates` monorepo. Read fully before starting. Stop and ask before deviating.

## Purpose

This template is one of several in a public library of Copier templates for AdaLab apps. A maintainer stamps it once into a demo repo, then re-brands that repo per-prospect by editing the logo file and three color tokens directly in-repo before each demo. The AdaLab Test → Build → Deploy cycle rebuilds the container and is an intentional part of the sales narrative ("every change, including branding, goes through the controlled pipeline"). During the live meeting, Claude Code inside AdaLab extends the app with business logic while guardrail hooks visibly prevent unsafe edits.

Three non-negotiable properties:

1. **The two baseline features (Departments, Employees) must be structurally identical file-for-file.** Claude Code pattern-matches the next feature against these; divergence creates demo unpredictability.
2. **Branding is in-repo files, not build-time questions and not runtime fetches.** One logo file and one CSS tokens file. You edit them directly; AdaLab rebuilds.
3. **Guardrails are defended in three layers** (CLAUDE.md intent, `permissions.deny` rules, PreToolUse hook script). Deny rules are "best-effort" per Anthropic's own docs; the hook is the real enforcement.

## Monorepo context

This template lives at `adamatics/app_coding_templates/fastapi-react-adalab/`. Multiple templates will live in the repo as parallel subdirectories. Users stamp this template with:

```bash
copier copy \
  gh:adamatics/app_coding_templates \
  --directory fastapi-react-adalab \
  <output-path> \
  --trust
```

Repo-root conventions (own `README.md`, template-author `CLAUDE.md`, monorepo `.claude/`) are covered in `REPO_SPEC.md`. This document covers only the `fastapi-react-adalab` template itself.

## Stack

- **Backend**: Python 3.11 (matches AdaLab's `python:3.11-slim`), uv (dev), pip in the container, FastAPI, SQLModel, pytest, ruff
- **Database**: SQLite at `/app/data/app.db` in the container; bind-mounted in local dev
- **Frontend**: Node 20, pnpm, Vite, React 18, TypeScript, TanStack Router, TanStack Query, React Hook Form, Zod
- **Deployment**: AdaLab via `Containerfile` + `.adalab/` config
- **Local dev**: `compose.local.yml` as optional convenience
- **Templating**: Copier, template source under `template/`, `.jinja` suffix

## AdaLab constraints (load-bearing)

From the `adalab-app-builder` skill. Any deviation will break deployment.

- **Single container.** Frontend builds to static assets; FastAPI serves them alongside the API.
- **File named `Containerfile`**, not `Dockerfile`.
- **Port 8000** for `port`, `test_serving_port`, and uvicorn's `--port`.
- **No nginx.** FastAPI + uvicorn serves everything.
- **Vite `base: './'`** so asset references are relative.
- **TanStack Router `basepath` set at runtime** from `window.location.pathname`.
- **`.adalab/app.json` has `stripped_prefix: true`**.
- **`.adalab/local_container_*.json` has `uid: 1`** (non-null placeholder; AdaLab overwrites on Build).
- **`.vscode/settings.json` has `{"adalab.workingMode": "appBuilder"}`**.
- **Deployment order: Test → Build → Deploy.** Skipping Build breaks first-time Deploy.

## Branding flow (in-repo, per-demo)

**Per-template demo repo lifecycle:**

1. Stamp the template once into a demo repo (e.g., `adamatics-demos/fastapi-react-demo`). Push.
2. Before each prospect meeting, edit the repo directly:
   - Replace `frontend/public/logo.svg` with the prospect's logo
   - Edit `frontend/src/styles/tokens.css`, changing three hex values on `--color-primary`, `--color-secondary`, `--color-accent`
   - Commit and push
3. In AdaLab: Test → Build → Deploy. Deployed app shows prospect branding.
4. During the meeting: Claude Code adds the Projects feature live; guardrails fire when prompted to weaken auth; rebuild shows the new feature deployed.
5. After the meeting: revert branding (`git checkout frontend/public/logo.svg frontend/src/styles/tokens.css`) or keep for the next prospect in the same industry.

**Consequences for the template:**

- `copier.yml` does **not** ask for logo or colors. The template ships with a neutral default logo and neutral colors.
- No `post_gen.py` branding logic. The hook script, if it exists at all, does only `chmod +x` on hook scripts and `git init`.
- The template's `frontend/src/styles/tokens.css` ships with real hex values (neutral defaults), not placeholders. No Jinja substitution needed.
- All frontend components use `var(--color-primary)` etc. **No hex literals in frontend source outside `tokens.css`.** Enforced by `.claude/rules/react-components.md`. Tokens.css itself is editable by Claude Code (with a prompt) for additive structural tokens, but the three brand hex values at the top of `:root` are documented as off-limits for feature work and are intended for human edits per-demo.

## Repository layout (stamped output)

```
<stamped-app>/
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── TEMPLATE_TODO.md
├── Containerfile
├── compose.local.yml              # optional local dev convenience
├── requirements.txt               # container dependency list
├── .env.example
├── .gitignore
├── .vscode/
│   └── settings.json
├── .adalab/
│   ├── app.json
│   ├── project.json
│   └── local_container_demo.json
├── .claude/
│   ├── settings.json
│   ├── rules/
│   │   ├── python-style.md
│   │   ├── feature-pattern.md
│   │   └── react-components.md
│   ├── agents/
│   │   ├── business-logic-implementer.md
│   │   └── security-reviewer.md
│   ├── commands/
│   │   ├── check.md
│   │   └── complete-projects.md
│   └── hooks/
│       └── protect_paths.py
├── main.py                        # FastAPI entry: API + static mount
├── pyproject.toml                 # dev project config (ruff, pytest)
├── uv.lock
├── app/                           # backend package
│   ├── __init__.py
│   ├── core/                      # PROTECTED
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── db.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # PROTECTED: aggregator with auto-discovery
│   │   ├── deps.py                # PROTECTED: auth dependencies
│   │   └── routes/                # OPEN (except _example.py if you ship one)
│   │       ├── __init__.py
│   │       ├── departments.py
│   │       ├── employees.py
│   │       └── projects.py        # stub with TODO header
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # PROTECTED
│   │   ├── department.py
│   │   ├── employee.py
│   │   └── project.py             # SQLModel defined, nothing else
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── department.py
│   │   └── employee.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── departments.py
│   │   ├── employees.py
│   │   └── projects.py            # stub
│   └── seed.py                    # seeds departments and employees on first run
├── tests/
│   ├── conftest.py
│   ├── api/
│   │   ├── test_departments.py
│   │   ├── test_employees.py
│   │   └── test_projects.py       # single skipped test
│   └── services/
│       ├── test_departments.py
│       └── test_employees.py
└── frontend/
    ├── package.json
    ├── pnpm-lock.yaml             # PROTECTED
    ├── vite.config.ts             # PROTECTED (base: './' is required)
    ├── tsconfig.json
    ├── index.html
    ├── public/
    │   └── logo.svg               # EDITED PER-DEMO (neutral default)
    └── src/
        ├── main.tsx               # PROTECTED: QueryClient + Router with basepath
        ├── routes/
        │   ├── __root.tsx
        │   ├── index.tsx
        │   ├── departments/
        │   │   ├── index.tsx
        │   │   ├── new.tsx
        │   │   └── $id.tsx
        │   ├── employees/
        │   │   ├── index.tsx
        │   │   ├── new.tsx
        │   │   └── $id.tsx
        │   └── projects/
        │       └── index.tsx      # "Coming soon" placeholder
        ├── styles/
        │   ├── tokens.css         # SENSITIVE: brand hex per-demo, structural tokens additive
        │   └── globals.css
        ├── components/
        │   ├── DataTable.tsx
        │   ├── FormField.tsx
        │   ├── ConfirmDialog.tsx
        │   └── AppHeader.tsx      # renders /logo.svg, uses tokens
        ├── api/
        │   ├── client.ts          # PROTECTED: auth header + basepath wiring
        │   ├── departments.ts
        │   └── employees.ts
        ├── lib/
        │   └── basepath.ts        # PROTECTED: AdaLab routing
        └── types/
            ├── department.ts
            └── employee.ts
```

Files marked `PROTECTED` are blocked by `protect_paths.py`. The comments above are for the human spec reader; do NOT add them as in-file sentinel comments except where explicitly specified below.

## Template source layout (what you build)

```
adamatics/app_coding_templates/fastapi-react-adalab/
├── SPEC.md                        # this file
├── README.md                      # usage: how to stamp and re-brand
├── copier.yml
├── hooks/
│   └── post_gen.py                # minimal: chmod and git init only
└── template/
    └── <all files from stamped output, with .jinja suffix on rendered files>
```

**Files rendered through Jinja** (add `.jinja` suffix in source):
- `README.md`, `CLAUDE.md`, `AGENTS.md`
- `.adalab/app.json`, `.adalab/local_container_demo.json`
- `main.py` (uses `{{ prospect_name }}` for `FastAPI(title=...)`)
- `frontend/package.json` (uses slug for `name`)

**Files copied verbatim** (no Jinja suffix):
- All Python source under `app/` and `tests/`
- All TS source including `main.tsx` (no prospect-name substitution needed)
- `Containerfile`, `requirements.txt`, `pyproject.toml`
- `frontend/src/styles/tokens.css` with neutral default colors (real hex, no placeholders)
- `frontend/public/logo.svg` (neutral placeholder logo)
- All `.claude/` content

## Copier configuration

`fastapi-react-adalab/copier.yml`:

```yaml
_min_copier_version: "9.3"
_subdirectory: template
_templates_suffix: .jinja
_answers_file: .copier-answers.yml
_skip_if_exists:
  - .env
  - .copier-answers.yml
  - frontend/public/logo.svg           # preserve per-demo edits
  - frontend/src/styles/tokens.css     # preserve per-demo edits

prospect_name:
  type: str
  help: Human-readable name (e.g. "Acme Corp"). Used as the app title and in .adalab config.

prospect_slug:
  type: str
  when: false
  default: "{{ prospect_name | lower | replace(' ', '-') | replace('.', '') | replace(',', '') }}"

app_description:
  type: str
  help: One-sentence description of the app
  default: "Internal app built on the Adamatics platform"

_tasks:
  - "chmod +x .claude/hooks/protect_paths.py"
  - "git init -b main"
```

Notice what's gone: no `logo_path`, no color questions, no `post_gen.py` branding logic. That's the point: branding is an in-repo edit after stamping.

`_skip_if_exists` on `logo.svg` and `tokens.css` means `copier update` won't overwrite your per-demo branding. If you later run `copier update` to pull in template improvements, your branding files are preserved.

## Data model

Three entities. Minimal fields, no PII-adjacent columns.

**Department**: `id`, `name` (unique, 1-100), `code` (unique, 2-10 chars uppercase), `description` (nullable, max 500), `created_at`.

**Employee**: `id`, `first_name` (1-50), `last_name` (1-50), `email` (unique, validated), `title` (1-100), `department_id` (FK, RESTRICT on delete), `hire_date`, `is_active` (default true), `created_at`.

**Project** (scaffolded only): `id`, `name`, `description` (nullable), `status` (Literal of planning/active/on_hold/completed), `department_id` (FK), `lead_employee_id` (FK nullable), `start_date`, `target_date` (nullable).

Define the `Project` SQLModel class in `app/models/project.py` and import it in `app/models/__init__.py` so metadata picks it up. The table gets created on startup alongside the others. Do not create routes/services/schemas/UI for Project beyond the stubs.

## Database

- DSN: `sqlite:///./data/app.db` (relative to app working dir)
- `app/core/db.py` creates the engine with `connect_args={"check_same_thread": False}`
- `main.py` startup: ensure `./data/` exists, `SQLModel.metadata.create_all(engine)`, then `seed_if_empty()`
- **No Alembic.** Schema changes are applied via `metadata.create_all()` at startup. Document this in CLAUDE.md so Claude doesn't invent migrations.
- `.gitignore` excludes `data/` and `*.db*`

## FastAPI application

### `main.py` at repo root

Single entry point:

```python
# main.py (sketch, not final)
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.main import include_all_routers
from app.core.db import init_db
from app.seed import seed_if_empty

app = FastAPI(title="{{ prospect_name }}")

@app.on_event("startup")
def startup():
    init_db()
    seed_if_empty()

include_all_routers(app, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok"}

STATIC = Path(__file__).parent / "static"
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        candidate = STATIC / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC / "index.html")
```

### `app/api/main.py` aggregator (protected)

Auto-discovers modules in `app/api/routes/` that define a `router` attribute, using `pkgutil.iter_modules`. Including Projects requires only creating the file; no edits here.

### `app/api/deps.py` (protected)

Dummy bearer auth: `Authorization: Bearer demo-token` passes, else 401. The guardrail moment in the demo is Claude being prompted to remove this and the hook blocking it.

### Router prefixes

Each entity's router: `APIRouter(prefix="/<plural>", tags=["<plural>"])`. The aggregator adds `/api` in front.

## Frontend structure

### TanStack Router with dynamic basepath (protected)

`src/lib/basepath.ts`:

```typescript
export function getBasename(): string {
  const path = window.location.pathname;
  const proxyMatch = path.match(/^(\/jupyterhub\/user\/[^/]+\/proxy\/\d+)/);
  if (proxyMatch) return proxyMatch[1];
  const appsMatch = path.match(/^(\/apps\/[^/]+)/);
  if (appsMatch) return appsMatch[1];
  return '';
}
```

`main.tsx` creates the router with `basepath: getBasename()`. `api/client.ts` prefixes every fetch with `getBasename() + '/api'`.

Verify after a build that `dist/index.html` references assets via `./assets/`, not `/assets/`.

### Styling

`src/styles/tokens.css` (the per-demo branding file):

```css
:root {
  /* Edit these three lines per-demo to re-brand. */
  --color-primary: #0B3D91;
  --color-secondary: #111827;
  --color-accent: #F5A623;

  /* Structural tokens: do not edit per-demo. */
  --color-bg: #ffffff;
  --color-text: #0a0a0a;
  --color-border: #e5e7eb;
  --radius-sm: 4px;
  --radius-md: 8px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
}
```

The three editable lines have an explicit comment. No templating. Branding is literal file editing.

**Rule: no hex literals anywhere in `frontend/src/` except `tokens.css`.** This is enforced by `.claude/rules/react-components.md` and checked during security review. When Claude implements Projects live, it must use `var(--color-primary)` so the reskin propagates.

### Protected frontend paths

Listed in the repository layout section above. Summary: `lib/basepath.ts`, `styles/tokens.css`, `api/client.ts`, `main.tsx`, `vite.config.ts`, `package.json`, `pnpm-lock.yaml`.

Note: `tokens.css` is both protected (from Claude Code) and edited per-demo (by you directly, outside Claude). The hook prevents Claude from touching it; you edit it by hand before demos. This asymmetry is intentional.

## Guardrail architecture (three layers)

Per the research report, deny rules alone are "best-effort" (Anthropic's own framing). Defend in depth:

### Layer 1: `CLAUDE.md` (intent)

Tells Claude where it may and may not edit. Persuasive, not enforceable. Under 120 lines. Uses `@AGENTS.md` and `@.claude/rules/*.md` imports.

### Layer 2: `.claude/settings.json` `permissions.deny` (fast, readable)

Regex-like patterns that Claude Code attempts to enforce. Fails gracefully on Bash compound commands and Grep subprocesses, which is exactly why Layer 3 exists.

### Layer 3: `.claude/hooks/protect_paths.py` (real enforcement)

PreToolUse hook. Exit code 2 blocks the tool call; stderr is fed back to Claude as feedback. Uses `$CLAUDE_PROJECT_DIR` for portability. Redundantly encodes the same protected paths as Layer 2, plus Bash command denylist. **This is the load-bearing layer.**

### Sensitive-but-editable tier

Five files are not in the hard-blocked tier but are documented as sensitive. They are gated through `permissions.ask` (so each edit prompts the human in-session) or are open with documented constraints:

- `requirements.txt`, `pyproject.toml` — open. After Python dep edits, run `uv sync` and `uv export --no-hashes --no-dev --no-emit-project > requirements.txt` to keep them in sync.
- `frontend/package.json` — open. After dep edits, `pnpm install` regenerates the lockfile.
- `.adalab/local_container_demo.json` — gated. Permitted edits: `environment_variables`, `max_ram`, `max_cpu`. Forbidden: `port`, `test_serving_port`, `uid`, `container_image_name`, `container_file`, `build_context`.
- `frontend/src/styles/tokens.css` — gated. Additive structural tokens permitted. The three brand hex values (`--color-primary`, `--color-secondary`, `--color-accent`) are off-limits for feature work; they're per-demo human edits.

The `business-logic-implementer` subagent's system prompt enumerates the same constraints. The hook's load-bearing protection covers auth, routing, ORM base, build pipeline, lockfiles, AdaLab identity (app.json, project.json), `.vscode/`, `.claude/` meta-config, and secrets — none of which the agent should ever edit.

## `.claude/settings.json`

```json
{
  "permissions": {
    "defaultMode": "default",
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(**/*.pem)",
      "Read(**/id_rsa*)",
      "Edit(./app/core/**)",
      "Edit(./app/api/main.py)",
      "Edit(./app/api/deps.py)",
      "Edit(./app/models/base.py)",
      "Edit(./main.py)",
      "Edit(./frontend/src/lib/basepath.ts)",
      "Edit(./frontend/src/styles/tokens.css)",
      "Edit(./frontend/src/api/client.ts)",
      "Edit(./frontend/src/main.tsx)",
      "Edit(./frontend/vite.config.ts)",
      "Edit(./frontend/package.json)",
      "Edit(./frontend/pnpm-lock.yaml)",
      "Edit(./.adalab/**)",
      "Edit(./.vscode/**)",
      "Edit(./Containerfile)",
      "Edit(./requirements.txt)",
      "Edit(./pyproject.toml)",
      "Edit(./uv.lock)",
      "Edit(./.claude/hooks/**)",
      "Edit(./.claude/settings.json)",
      "Bash(rm -rf:*)",
      "Bash(git push:*)",
      "Bash(uv add:*)",
      "Bash(pip install:*)",
      "Bash(pnpm add:*)",
      "Bash(npm install:*)"
    ],
    "ask": [
      "Bash(git commit:*)"
    ],
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run ruff:*)",
      "Bash(uv run uvicorn main:app:*)",
      "Bash(pnpm run dev:*)",
      "Bash(pnpm run test:*)",
      "Bash(pnpm run build:*)",
      "Bash(pnpm run lint:*)",
      "Bash(pnpm install --frozen-lockfile)",
      "WebFetch(domain:fastapi.tiangolo.com)",
      "WebFetch(domain:docs.pydantic.dev)",
      "WebFetch(domain:tanstack.com)",
      "WebFetch(domain:sqlmodel.tiangolo.com)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|Read|Bash",
        "hooks": [{
          "type": "command",
          "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect_paths.py"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [{
          "type": "command",
          "command": "uv run ruff format \"$CLAUDE_TOOL_INPUT_FILE_PATH\" 2>/dev/null; uv run ruff check --fix \"$CLAUDE_TOOL_INPUT_FILE_PATH\" 2>/dev/null; cd \"$CLAUDE_PROJECT_DIR/frontend\" && pnpm exec prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\" 2>/dev/null; true"
        }]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [{
          "type": "command",
          "command": "echo '[AdaLab demo template] Guardrails active. Protected zones enforced by .claude/hooks/protect_paths.py. See CLAUDE.md for editable/protected zones.'"
        }]
      }
    ]
  }
}
```

Critical details (from the report):

- `PreToolUse` hook uses `$CLAUDE_PROJECT_DIR`, not `./`
- PostToolUse formatter ends with `; true` so a failing format doesn't cascade
- **Exit code 2 blocks; exit code 1 does not.** The hook script must use `sys.exit(2)` on block.
- JSON stdout returning `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}` blocks even in `bypassPermissions` mode (useful if a user accidentally sets that mode)

## `.claude/hooks/protect_paths.py`

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
"""PreToolUse hook: blocks edits to protected paths and dangerous bash.

Exit 2 blocks the tool call and feeds stderr back to Claude as guidance.
Exit 0 allows it. Exit 1 does NOT block (common footgun); avoid.
"""
import json
import os
import re
import sys

PROTECTED_PATHS = [
    # Backend infrastructure
    r"^app/core/",
    r"^app/api/main\.py$",
    r"^app/api/deps\.py$",
    r"^app/models/base\.py$",
    r"^main\.py$",
    # Frontend infrastructure
    r"^frontend/src/lib/basepath\.ts$",
    r"^frontend/src/styles/tokens\.css$",
    r"^frontend/src/api/client\.ts$",
    r"^frontend/src/main\.tsx$",
    r"^frontend/vite\.config\.ts$",
    r"^frontend/package\.json$",
    r"^frontend/pnpm-lock\.yaml$",
    # Platform and build
    r"^\.adalab/",
    r"^\.vscode/",
    r"^Containerfile$",
    r"^requirements\.txt$",
    r"^pyproject\.toml$",
    r"^uv\.lock$",
    # Claude Code config itself
    r"^\.claude/hooks/",
    r"^\.claude/settings\.json$",
    # Secrets
    r"^\.env(\.|$)",
    r"\.pem$",
    r"\.key$",
]

DANGEROUS_BASH = [
    (r"\brm\s+-[a-z]*r[a-z]*f", "rm -rf variants are blocked"),
    (r"\bcurl\b[^|]*\|\s*(sh|bash)", "curl | shell is blocked"),
    (r"\bgit\s+push\b", "git push is blocked; human will push"),
    (r"\b(uv|pip)\s+add\s+", "dependency additions must be human-approved"),
    (r"\b(pnpm|npm|yarn)\s+(add|install)\s+[^-]", "dependency additions must be human-approved"),
]


def block(reason: str) -> None:
    print(f"BLOCKED by .claude/hooks/protect_paths.py: {reason}", file=sys.stderr)
    # Also emit JSON that blocks in bypassPermissions mode.
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(2)


def relpath(abs_path: str) -> str:
    base = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    try:
        return os.path.relpath(abs_path, base)
    except ValueError:
        return abs_path


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # do not block on malformed input

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}

    if tool in ("Edit", "Write", "MultiEdit"):
        path = inp.get("file_path") or inp.get("path") or ""
        rel = relpath(path)
        for pat in PROTECTED_PATHS:
            if re.search(pat, rel):
                block(f"{rel} is in a protected zone. Ask the human to edit it directly.")

    if tool == "Read":
        path = inp.get("file_path") or ""
        if re.search(r"(^|/)\.env(\.|$)", path) or path.endswith((".pem", ".key", "id_rsa")):
            block("Secret files are not readable. Reference .env.example if you need environment variable names.")

    if tool == "Bash":
        cmd = inp.get("command", "")
        for pat, reason in DANGEROUS_BASH:
            if re.search(pat, cmd):
                block(f"Command matches deny pattern: {reason}")
        # Also block attempts to read protected files via cat/less/head/tail
        for pat in PROTECTED_PATHS:
            if re.search(rf"\b(cat|less|more|head|tail|bat)\b.*{pat}", cmd):
                block(f"Reading protected file via shell is blocked.")
        if re.search(r"\bcat\b.*\.env", cmd) or re.search(r"\becho\b.*\$\{?[A-Z_]*SECRET", cmd):
            block("Attempt to read or echo secrets is blocked.")

    sys.exit(0)


if __name__ == "__main__":
    main()
```

This is longer than the v2 sketch because it now includes the Bash-reading-protected-files check (closes the "`cat .env` bypasses `Read(./.env)` deny" hole from the report), and the JSON-stdout block for `bypassPermissions` resilience.

## `.claude/rules/` files

Path-scoped rules using YAML frontmatter so they load only when Claude touches matching files. Keeps the base CLAUDE.md lean.

### `.claude/rules/feature-pattern.md`

```markdown
---
paths: ["app/api/routes/**", "app/services/**", "app/schemas/**", "app/models/**", "tests/**"]
---
# Backend feature pattern

Every entity `X` has these six files, in this order of creation:

1. `app/models/x.py`: SQLModel class. Import it in `app/models/__init__.py`.
2. `app/schemas/x.py`: `XCreate`, `XUpdate`, `XRead`.
3. `app/services/x.py`: module-level functions `list_x(session, skip, limit)`, `get_x(session, id)`, `create_x(session, data)`, `update_x(session, id, data)`, `delete_x(session, id)`. No classes.
4. `app/api/routes/x.py`: `router = APIRouter(prefix="/xs", tags=["xs"])` and 5 endpoints (GET list, GET one, POST, PATCH, DELETE). All depend on `get_current_user` from `deps.py`.
5. `tests/services/test_x.py`: unit tests per service function.
6. `tests/api/test_x.py`: at minimum `test_list_empty`, `test_create_and_get`, `test_create_duplicate_fails`, `test_update`, `test_delete`, `test_unauthenticated_returns_401`.

Model your new entity file-for-file on `app/api/routes/departments.py` etc. Do not invent new patterns.
```

### `.claude/rules/react-components.md`

```markdown
---
paths: ["frontend/src/**"]
---
# React component rules

- No hex literals anywhere under `frontend/src/` except `styles/tokens.css`. Use `var(--color-primary)`, `var(--color-secondary)`, `var(--color-accent)`.
- Every new page under `src/routes/xs/` uses `DataTable`, `FormField`, `ConfirmDialog` from `components/`.
- Every data fetch uses TanStack Query hooks defined in `src/api/x.ts`.
- Every form uses React Hook Form + Zod.
- Never import from `frontend/src/lib/basepath.ts`, `frontend/src/api/client.ts`, or `frontend/src/main.tsx` except in files that already do.
```

### `.claude/rules/python-style.md`

```markdown
---
paths: ["**/*.py"]
---
# Python style

- Python 3.11 syntax. Use `str | None`, not `Optional[str]`.
- Type hints on every function parameter and return.
- SQLModel for all DB models. Never raw SQL.
- Pydantic v2 for schemas. Separate `Create`, `Update`, `Read`.
- Services return domain objects or raise exceptions. Routes catch and translate to HTTPException.
- Tests use `pytest`, not `unittest`. Use fixtures from `conftest.py`.
```

## `.claude/agents/`

### `business-logic-implementer.md`

```yaml
---
name: business-logic-implementer
description: Use PROACTIVELY to add new routes, SQLModel entities, services, and React pages. Do not modify infrastructure.
tools: Read, Grep, Glob, Edit, Write, Bash
permissionMode: default
model: inherit
---
You implement business logic in this AdaLab app template. You never edit:

- app/core/**, app/api/main.py, app/api/deps.py, main.py
- frontend/src/lib/**, frontend/src/api/client.ts, frontend/src/main.tsx, frontend/src/styles/tokens.css
- .adalab/**, Containerfile, requirements.txt, pyproject.toml
- .claude/** (except rules/ if adding a new rule)

Follow `.claude/rules/feature-pattern.md` for the backend pattern and `.claude/rules/react-components.md` for the frontend.

Before declaring done:
1. `uv run pytest -q` passes
2. `uv run ruff check` passes
3. `cd frontend && pnpm run test` passes

Do not commit. Do not push. The human will review and commit.
```

### `security-reviewer.md`

```yaml
---
name: security-reviewer
description: Read-only auditor. MUST BE USED before commit after any change to routes, models, services, or UI.
tools: Read, Grep, Glob, Bash
permissionMode: plan
model: opus
---
You are a security auditor for a FastAPI + React app deployed on AdaLab. You have no write tools.

Produce a severity-tagged report (critical/high/medium/low/info) covering:

- AuthN/AuthZ: every new route has a `get_current_user` dependency
- Input validation: all inputs have Pydantic or Zod schemas, no raw `str` accepted unvalidated
- SQL injection: no raw SQL strings; all queries use SQLModel/SQLAlchemy
- Secret leakage: no `print()` or `logger.info()` of env vars, tokens, or user data
- Exception handling: no broad `except Exception:` that hides 401/403
- CORS/CSRF: no permissive CORS added; SameSite cookies if any added
- Hex literals in frontend src outside tokens.css (informational)

Only flag issues you are >80% sure are real. If uncertain, flag as `info`.
```

**Note on subagent scoping** (from the report): `security-reviewer` has `tools: Read, Grep, Glob, Bash` (no Edit/Write). This is blast-radius reduction at the subagent level. `business-logic-implementer` can write, but its `permissionMode: default` means the hook still fires on every tool call. Never set `permissionMode: bypassPermissions` in any template subagent.

## `.claude/commands/`

### `check.md`

```markdown
---
allowed-tools: Bash(uv run pytest:*), Bash(uv run ruff:*), Bash(pnpm run test:*), Bash(pnpm run lint:*)
description: Run the full check suite (backend tests, lint, frontend tests)
---
Run all of the following in sequence. Report failures. Do not attempt fixes unless I explicitly ask.

1. `uv run pytest -q`
2. `uv run ruff check`
3. `cd frontend && pnpm run test`
4. `cd frontend && pnpm run lint`
```

### `complete-projects.md`

```markdown
---
description: Complete the Projects feature following the Departments/Employees pattern.
---
Read `TEMPLATE_TODO.md` and `.claude/rules/feature-pattern.md`.

Complete the Projects feature by mirroring `app/api/routes/departments.py`, `app/services/departments.py`, `app/schemas/departments.py` (copy, then change field names to match the Project model). Do the same for the frontend under `frontend/src/routes/projects/`.

Then:
1. Unskip `tests/api/test_projects.py` and implement the tests mirroring `test_departments.py`.
2. Run `/check`.
3. Stop. Do not commit. Report what you did.
```

## `TEMPLATE_TODO.md`

```markdown
# Template TODO

## Projects feature (incomplete)

The `Project` SQLModel is defined; routes, service, schemas, UI, and tests are stubs. To complete:

1. Create `app/schemas/project.py` with `ProjectCreate`, `ProjectUpdate`, `ProjectRead`.
2. Implement `app/services/projects.py`, mirroring `app/services/departments.py`.
3. Implement `app/api/routes/projects.py`, mirroring `app/api/routes/departments.py`. The aggregator will pick it up automatically.
4. Add `frontend/src/types/project.ts` and `frontend/src/api/projects.ts`.
5. Implement `frontend/src/routes/projects/index.tsx`, `$id.tsx`, `new.tsx`.
6. Unskip and implement `tests/api/test_projects.py`.
7. Run `uv run pytest -q && cd frontend && pnpm run test`.
8. Rebuild via AdaLab Test → Build → Deploy to see it live.

Do not create migrations. Schema changes happen via `SQLModel.metadata.create_all()` at startup.
```

## Root `CLAUDE.md` (rendered from `.jinja`)

Keep under 120 lines. Structure:

```markdown
# {{ prospect_name }}

@AGENTS.md

## Stack
FastAPI + SQLModel + SQLite + TanStack Router. Deployed on AdaLab.

## Commands
- Dev backend: `uv run uvicorn main:app --reload`
- Dev frontend: `cd frontend && pnpm run dev`
- Tests: `uv run pytest -q && cd frontend && pnpm run test`
- Lint: `uv run ruff check && cd frontend && pnpm run lint`
- Local container build: `docker compose -f compose.local.yml up --build`

## You MAY edit
- `app/api/routes/**` (except `main.py` and `deps.py`)
- `app/models/**` (except `base.py`; add new models, import them in `__init__.py`)
- `app/services/**`
- `app/schemas/**`
- `frontend/src/routes/**`
- `frontend/src/components/**`
- `frontend/src/api/*.ts` (except `client.ts`)
- `frontend/src/types/**`
- `tests/**`

## You MUST NOT edit (blocked by .claude/hooks/protect_paths.py)
- `app/core/**`, `app/api/main.py`, `app/api/deps.py`, `app/models/base.py`, `main.py`
- `frontend/src/lib/basepath.ts`, `frontend/src/styles/tokens.css`, `frontend/src/api/client.ts`, `frontend/src/main.tsx`, `frontend/vite.config.ts`
- `.adalab/**`, `.vscode/**`, `Containerfile`, `requirements.txt`, `pyproject.toml`, `uv.lock`
- `frontend/package.json`, `frontend/pnpm-lock.yaml`
- `.env*` (read or write), `.claude/hooks/**`, `.claude/settings.json`

If you believe a protected file must change, stop and explain why. Do not attempt workarounds.

## Extending
Read `.claude/rules/feature-pattern.md` before adding a route. Read `.claude/rules/react-components.md` before adding a page. Read `TEMPLATE_TODO.md` for what's currently incomplete.

## Deployment
This app deploys to AdaLab via Test → Build → Deploy in the AdaLab VS Code extension. Do not invoke AdaLab commands yourself; the human drives the deploy.

## Database
SQLite at `./data/app.db`. Schema changes via `SQLModel.metadata.create_all()` on startup. Do not add Alembic.

## Workflow
1. Read the feature request and any relevant `.claude/rules/` files.
2. Propose a plan before editing multi-file work.
3. Implement, then run `/check`.
4. Invoke the `security-reviewer` agent before declaring done.
5. Do not commit. The human will review and commit.
```

## Containerfile

Multi-stage. Frontend builds first, then copies its `dist/` into the Python image as `./static/`.

```dockerfile
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ .
RUN pnpm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
COPY main.py ./
COPY app/ ./app/
COPY --from=frontend /app/frontend/dist ./static
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`requirements.txt` is generated from `pyproject.toml` via `uv export --no-hashes > requirements.txt`. Both files are committed. Document this in CLAUDE.md so Claude understands why they both exist.

## `.adalab/` configuration

`app.json` (rendered):

```json
{
    "app_id": null,
    "app_name": "{{ prospect_name }}",
    "app_description": "{{ app_description }}",
    "app_url": "{{ prospect_slug }}",
    "stripped_prefix": true,
    "access_level": "logged_in",
    "acl_userlist": [],
    "acl_group_names": [],
    "idp_enabled": false,
    "idp_scope": null,
    "maintainers": []
}
```

`project.json` (verbatim):

```json
{"type": "appBuilder"}
```

`local_container_demo.json` (rendered):

```json
{
    "uid": 1,
    "container_image_name": "{{ prospect_slug }}-demo",
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

`.vscode/settings.json` (verbatim):

```json
{"adalab.workingMode": "appBuilder"}
```

## Local dev compose (optional)

`compose.local.yml`:

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    environment:
      PYTHONUNBUFFERED: "1"
```

## Definition of done

The template is complete when all of the following hold:

1. `copier copy . --directory fastapi-react-adalab /tmp/test-stamp --trust --data prospect_name="Test Co" --data app_description="A test"` produces a directory
2. `cd /tmp/test-stamp && docker build -t test -f Containerfile .` builds without errors
3. `docker run -p 8000:8000 test` starts; `curl http://localhost:8000/api/health` returns `{"status":"ok"}`
4. `curl -H "Authorization: Bearer demo-token" http://localhost:8000/api/departments` returns 5 seeded departments
5. Browser at `http://localhost:8000/` shows the neutral-default logo and colors, and navigable Departments and Employees lists
6. Editing `frontend/src/styles/tokens.css` (changing the three `--color-*` values) and `frontend/public/logo.svg`, then rebuilding the container, produces a visibly different app
7. `dist/index.html` references assets via `./assets/` (relative)
8. `uv run pytest` passes with zero failures and exactly one skip (Projects stub)
9. `cd frontend && pnpm run test` passes
10. Opening Claude Code in the stamped dir and asking it to edit `app/core/security.py` produces `BLOCKED by .claude/hooks/protect_paths.py` within 2 seconds
11. Asking Claude Code to `cat .env` produces a block (closes the Bash-bypass hole)
12. Invoking `/complete-projects` produces a working Projects feature; tests pass; rebuild shows it deployed
13. After step 12, asking "remove authentication from the projects route" is blocked by the hook
14. The template deploys successfully to AdaLab via Test → Build → Deploy
15. After stamping, asking Claude Code to add a dummy Python dep (e.g. `requests`) results in: pyproject.toml updated, `uv sync` run, requirements.txt regenerated. No hook block.
16. After stamping, asking Claude Code to add a chart token to `tokens.css` triggers a `permissions.ask` prompt; on approve, the edit succeeds; the three brand hex values are not changed.

## Build order

Follow this order. Commit after each step. Each commit is a git reset target.

1. Repo skeleton at `adamatics/app_coding_templates/fastapi-react-adalab/`: `copier.yml`, `README.md`, `SPEC.md` (this file), empty `hooks/post_gen.py`, empty `template/`
2. Backend skeleton: `pyproject.toml`, `main.py` (minimal, health endpoint only), `app/core/{config,db,security}.py`, `app/api/{main,deps}.py`, `app/models/base.py`, `app/__init__.py` files
3. Department slice end-to-end: model → schema → service → route → service tests → API tests
4. Employee slice: **copy Department files verbatim, change field names only**. Verify side-by-side that the two slices are structurally identical.
5. Project stubs: `app/models/project.py` with SQLModel, stub files for schemas/services/routes/tests with TODO headers only
6. `seed.py` with 5 departments + 20 employees; wire into startup
7. Frontend skeleton: Vite scaffold, TanStack Router + Query, `main.tsx`, `__root.tsx`, `lib/basepath.ts`, `api/client.ts`, `styles/tokens.css` (with neutral defaults), `components/{DataTable,FormField,ConfirmDialog,AppHeader}.tsx`
8. Frontend Department routes: list + detail + new
9. Frontend Employee routes: copy Department routes verbatim, change fields only
10. Frontend Projects stub route ("Coming soon")
11. `Containerfile`, `requirements.txt` (`uv export --no-hashes > requirements.txt`)
12. Local compose verify: `docker compose -f compose.local.yml up --build` starts, UI renders, both entities CRUD correctly
13. `.adalab/` files, `.vscode/settings.json`
14. **AdaLab deployment smoke test**: push stamped repo to a private GitHub repo, import into AdaLab, Test → Build → Deploy, verify URL renders
15. `.claude/` configuration: `settings.json`, `hooks/protect_paths.py`, `rules/*.md`, `agents/*.md`, `commands/*.md`
16. `CLAUDE.md`, `AGENTS.md`, `TEMPLATE_TODO.md`
17. Move content into `template/` under `.jinja` suffixes where needed; verify `copier copy` renders cleanly
18. End-to-end validation: all 14 Definition of Done items
19. **Per-demo branding dry run**: edit `tokens.css` and `logo.svg` in the stamped repo, rebuild the container, verify the reskin propagates visually

## What to stop and ask about

- Any field added or removed from the data model
- Any structural divergence between Department and Employee slices
- Any hex literal in `frontend/src/` outside `tokens.css`
- Any deviation from the directory layout
- Any protected-zone edit (the hook should catch this; if you think it's needed, stop and flag)
- Adding a dependency that wasn't on the implicit roadmap (e.g. switching ORMs, adding a job queue) — declare and confirm before editing pyproject.toml or package.json.
- Any attempt to add Alembic or database migrations
- Any attempt to use separate frontend and backend containers
- Any attempt to use nginx
- Any attempt to bind to a port other than 8000
- Any CSS framework (no Tailwind, no MUI, no Chakra; plain CSS with tokens)
- Any `permissionMode: bypassPermissions` in subagents
- Any MCP server configuration (out of scope for this template)
