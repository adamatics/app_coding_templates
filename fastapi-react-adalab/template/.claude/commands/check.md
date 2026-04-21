---
allowed-tools: Bash(uv run pytest:*), Bash(uv run ruff:*), Bash(pnpm run test:*), Bash(pnpm run lint:*)
description: Run the full check suite (backend tests, lint, frontend tests)
---
Run all of the following in sequence. Report failures. Do not attempt fixes unless I explicitly ask.

1. `uv run pytest -q`
2. `uv run ruff check`
3. `cd frontend && pnpm run test`
4. `cd frontend && pnpm run lint`
