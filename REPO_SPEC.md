# adamatics/app_coding_templates: Monorepo Spec

This repo hosts multiple Copier templates for AdaLab apps. Each template is a self-contained subdirectory. This document covers shared conventions across all templates.

## Purpose

Provide a curated set of AdaLab-ready app templates that maintainers stamp out, brand per-prospect by editing in-repo files, deploy via the AdaLab extension, and extend with Claude Code. Every template must:

- Build and deploy cleanly on AdaLab (port 8000, Containerfile, FastAPI + uvicorn, `stripped_prefix: true`)
- Ship a `.claude/` directory with three layers of guardrails (CLAUDE.md intent, `permissions.deny`, PreToolUse hook)
- Document what is editable and what is protected
- Apply prospect branding via in-repo file edits (logo file + three CSS hex tokens), not via Copier questions
- Use a generic data model (Departments/Employees/Projects for the reference template; analogous generic entities for others)

## Monorepo layout

```
adamatics/app_coding_templates/
├── README.md                     # index of templates and usage
├── REPO_SPEC.md                  # this file
├── CLAUDE.md                     # for template authors using Claude Code in this repo
├── .claude/                      # template-author tooling; NOT stamped into outputs
│   ├── settings.json
│   └── agents/
│       └── template-author.md
├── fastapi-react-adalab/         # the first template
│   ├── SPEC.md                   # template-specific spec (authoritative for builds)
│   ├── README.md                 # how to stamp and re-brand
│   ├── copier.yml
│   ├── hooks/
│   │   └── post_gen.py
│   └── template/
│       └── <stamped output contents>
├── <future-template>/            # e.g., streamlit-adalab, nextjs-adalab, fastapi-only
└── examples/                     # optional: reference stamped outputs
    └── .gitignore                # contents gitignored
```

## Conventions every template must follow

**1. Self-contained subdirectory.** No shared files across templates. If two templates need the same `protect_paths.py`, duplicate it. Drift is acceptable; cross-template coupling is not. (Decision rationale: pre-optimizing for DRY across templates that don't exist yet is a common failure mode.)

**2. Stamped via `--directory`.** The usage command is always:

```bash
copier copy \
  gh:adamatics/app_coding_templates \
  --directory <template-name> \
  <output-path> \
  --trust
```

Document this in each template's `README.md`.

**3. Minimal Copier questions.** Every template asks for:

- `prospect_name` (str): human-readable, used in `.adalab/app.json` as `app_name`
- `prospect_slug` (str, computed): derived from name, used as `app_url` and container image name
- `app_description` (str): one sentence, used in `.adalab/` config

**No branding questions in Copier.** Branding is an in-repo file edit after stamping. Specifically: `frontend/public/logo.svg` and three hex values in `frontend/src/styles/tokens.css`. This keeps the stamped repo durable across multiple prospect demos.

**4. `_skip_if_exists` for branding files.** Every `copier.yml` must list:

```yaml
_skip_if_exists:
  - frontend/public/logo.svg
  - frontend/src/styles/tokens.css
  - .env
  - .copier-answers.yml
```

So that `copier update` (pulling in template improvements later) does not clobber per-demo branding edits.

**5. `.adalab/` directory present** with `app.json`, `project.json`, `local_container_*.json`, and `.vscode/settings.json` at the repo root. Values match the AdaLab skill's requirements (port 8000, `stripped_prefix: true`, `uid: 1`).

**6. `Containerfile` at repo root.** Not `Dockerfile`. Multi-stage if frontend is involved. Final stage is `python:3.11-slim` with FastAPI + uvicorn on port 8000.

**7. Three-layer guardrails in the stamped output's `.claude/`:**

- **Layer 1, intent**: `CLAUDE.md` with editable/protected zone lists and `@AGENTS.md` import. Under 120 lines.
- **Layer 2, best-effort**: `.claude/settings.json` with `permissions.deny` patterns.
- **Layer 3, real enforcement**: `.claude/hooks/protect_paths.py`. Must use `sys.exit(2)` to block, must use `$CLAUDE_PROJECT_DIR` for path resolution, must cover both file-path Edit/Write blocks and Bash command denylist, must close the `cat .env` via Bash hole.

**8. At least two subagents:**

- `business-logic-implementer.md`: full tool access except for its system prompt restrictions, `permissionMode: default` (never `bypassPermissions`).
- `security-reviewer.md`: read-only tools (`Read, Grep, Glob, Bash`), `permissionMode: plan`, Opus model. This is blast-radius reduction at the subagent level.

**9. Path-scoped rule files.** Use YAML frontmatter `paths:` globs on `.claude/rules/*.md` so rules load only when Claude touches matching files. Keeps the root `CLAUDE.md` lean.

**10. `SPEC.md` at each template's source root** (next to `copier.yml`). This is what Claude Code reads when you work on the template itself. It should contain: purpose, stack, constraints, repository layout, data model, protected zones, `.claude/` configuration, Definition of Done, build order.

## Repo-root `CLAUDE.md` (for template authors)

When you work on this repo with Claude Code, Claude operates on template sources, not stamped outputs. Different rules apply.

Contents:

- How templates are organized (one subdir each, Copier-based, self-contained)
- The conventions above, enforced by review (not by hooks at this level, because the hooks in each template's `template/.claude/` only activate after stamping)
- How to add a new template (copy an existing template, rewrite `SPEC.md`, adjust `copier.yml`, adjust `template/` stack, test end-to-end)
- How to test a template: stamp to `/tmp/test-<n>`, build the Containerfile, run the container, verify the Definition of Done in that template's `SPEC.md`
- Do not stamp templates casually during a Claude Code session; ask the human first
- When working on a specific template, cd into that template's subdirectory before opening Claude Code, so Claude's working context is scoped

## Repo-root `.claude/` configuration

Minimal. The goal is protecting template sources from accidental edits when Claude is working on one template and might reach into another.

`.claude/settings.json`:

```json
{
  "permissions": {
    "defaultMode": "default",
    "deny": [
      "Edit(./fastapi-react-adalab/template/.claude/hooks/**)",
      "Edit(./README.md)",
      "Edit(./REPO_SPEC.md)",
      "Edit(./CLAUDE.md)",
      "Bash(git push:*)",
      "Bash(rm -rf:*)",
      "Bash(copier copy:*)",
      "Bash(copier update:*)"
    ]
  }
}
```

When working on a specific template, launch the Claude Code session from that subdirectory (`cd fastapi-react-adalab && claude`). This gives Claude a natural working radius that matches the template scope.

## Adding a new template

1. Copy an existing template: `cp -r fastapi-react-adalab my-new-template`
2. Rewrite `SPEC.md` for the new template's purpose, stack, data model, Definition of Done
3. Update `copier.yml` if questions differ (the minimum three must remain)
4. Update `hooks/post_gen.py` if stamp-time logic differs (should stay minimal)
5. Rewrite `template/` for the new stack: replace FastAPI + React with whatever the new template's stack is. Keep the `.adalab/` config, the `Containerfile`, the three-layer `.claude/` guardrails.
6. Verify end-to-end against the new `SPEC.md`'s Definition of Done
7. Verify an AdaLab deployment: stamp, push, Test → Build → Deploy, confirm the app loads
8. Update the repo `README.md` to list the new template
9. Open a PR

## Testing templates in CI (future)

Out of scope for the initial build but worth noting:

- Per template: stamp to a temp directory with canned inputs
- Build the Containerfile
- Run the container, verify `/api/health`
- Run the template's test suite if present
- Do not attempt AdaLab deployment from CI (requires platform credentials and is brittle)

## Branding fallback contract: 
Every template's frontend/public/logo.svg and frontend/src/styles/tokens.css ship with Adamatics defaults. The app_template_builder card overwrites these at stamp time with files from ~/shared/demo_branding/ if present. Templates must not put prospect-specific content in any other file; the two files above are the only branding contract.

## Template design decisions to preserve

These were resolved during initial design. Future templates should follow unless there's a specific reason not to:

- **Copier, not Cookiecutter.** Copier's native `copier update` is load-bearing because template fixes should propagate to stamped demo repos. Cruft is not a substitute.
- **SQLite, not Postgres, for demo templates.** AdaLab's single-container constraint makes sidecar databases expensive. SQLite is zero-config, fits in one container, and adequate for the data scales in demos.
- **No Alembic.** `SQLModel.metadata.create_all()` at startup is fine for demo scale. Alembic is overhead that domain experts won't maintain.
- **No Tailwind/MUI/Chakra.** Plain CSS with custom properties is the most predictable thing for Claude to extend. CSS frameworks drag in conventions that compete with the template's own rules.
- **Branding as in-repo file edits, not runtime fetches, not Copier questions.** AdaLab doesn't mount `/shared`. The rebuild cycle is part of the demo story. Runtime fetches would add fragility for no benefit.
- **`permissionMode: default` in every writable subagent.** Never `bypassPermissions`, not even "just for the demo."
- **Subagents never spawn other subagents.** (This is a platform constraint, but worth noting so template authors don't try.)
- **MCP servers not bundled.** Adds supply-chain risk and attack surface for demos. Revisit for customer-grade templates later.

## Known open questions for later

- Whether `copier update` on stamped demo repos is worth the complexity given that demos are typically short-lived. Likely yes, because a fix to the Projects pattern in the template should propagate.
- Whether a shared `.claude/hooks/protect_paths.py` library (symlinked into each template) would be worth the DRY at 5+ templates. Revisit when that threshold is hit; duplication is fine until then.
- Whether to add an `examples/` directory with pre-stamped outputs for smoke testing. Defer until there's a concrete reason.

