# Contributing to rekipedia

Thanks for your interest in contributing! This guide covers everything you need to get started.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Running Tests](#running-tests)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Release Process](#release-process)
- [Code Style](#code-style)

---

## Development Setup

```bash
git clone https://github.com/unrealandychan/rekipedia.git
cd rekipedia

# Install in editable mode with dev extras
uv sync --dev
# or: pip install -e ".[dev]"

# Smoke test
rekipedia --version
```

Requires **Python 3.11+** and [uv](https://github.com/astral-sh/uv) (or pip).

---

## Project Structure

```
rekipedia/
├── src/rekipedia/            # Python package
│   ├── cli/                  # Click CLI entrypoints
│   ├── llm/                  # LLMClient + LLMCaller Protocol
│   ├── orchestrator/         # run_ask, run_digest
│   ├── server/               # FastAPI app
│   ├── storage/              # SQLite store
│   └── synthesis/            # PlannerAgent + PageBuilder
├── tests/                    # Python pytest suite
└── .github/workflows/        # CI/CD
```

---

## Making Changes

1. **Fork** the repo and create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```

2. Follow **[Conventional Commits](https://www.conventionalcommits.org/)**:
   ```
   feat(server): add pagination to /api/pages
   fix(security): sanitize slug before file lookup
   docs: update README examples
   refactor(llm): extract Caller interface
   ```

3. Keep commits **focused** — one logical change per commit.

---

## Running Tests

```bash
# Run full suite
uv run pytest tests/ -v

# With coverage report
uv run pytest tests/ --cov=src/rekipedia --cov-report=term-missing

# CI enforces minimum 60% coverage — PRs that drop below will fail
```

---

## Submitting a Pull Request

1. Ensure all tests pass locally.
2. Run `uv run ruff check src/ tests/` for Python linting.
3. Open a PR against `main` with a clear description of **what** and **why**.
4. Reference any related issues (`Closes #N`).

PRs must pass all CI checks before merging:
- Python CI: build + smoke test + pytest + coverage gate (Python 3.11, 3.12)

---

## Release Process

```bash
# Python release (publishes to PyPI via hatch)
git tag py/v1.3.0
git push origin py/v1.3.0
```

---

## Code Style

### Python
- [Ruff](https://docs.astral.sh/ruff/) for linting + formatting.
- Type hints required for all public functions.
- Use `LLMCaller` Protocol for dependency injection — pass `caller=FakeCaller(...)` in tests instead of mocking litellm.

---

## Docker Sandbox

`DockerSandboxRunner` runs the rekipedia extractor pipeline inside an isolated Docker container so that untrusted repository code cannot make outbound network calls or affect the host filesystem. The repo is mounted **read-only**, the container runs with `--network none`, and LLM calls happen on the host after extraction completes. When Docker is available and the sandbox image is present, `get_runner()` selects it automatically; otherwise it falls back to `LocalRunner` (in-process).

### Building the sandbox image

A `Dockerfile.sandbox` is included in the repo root:

```bash
docker build -f Dockerfile.sandbox -t rekipedia-sandbox:latest .
```

### Activating the Docker sandbox

Once the image is built, the sandbox is activated **automatically** the next time you run any `reki` command — no extra flags needed. `get_runner()` detects the image via `docker image inspect rekipedia-sandbox:latest` and selects `DockerSandboxRunner` when found.

To force the in-process runner even when the image is present, pass `force_local=True` to `get_runner()` programmatically or simply remove/retag the image.

---

## AgentPlanner (Experimental)

`AgentPlanner` is an **experimental** multi-turn, tool-calling wiki planner. Instead of generating a single-shot JSON plan, the LLM incrementally builds the wiki structure by calling `add_section`, `add_page`, and `finalize` tools across up to 20 iterations. This produces richer, more coherent wiki layouts at the cost of extra LLM round-trips.

### Activating AgentPlanner

Set the environment variable `REKIPEDIA_AGENT_PLANNER=1` before running a scan:

```bash
REKIPEDIA_AGENT_PLANNER=1 reki scan .
```

The default (`0`) uses the standard single-shot planner.

### Current status

AgentPlanner is **experimental** — it works but has not been hardened for production use. There is currently no graduation plan or timeline for promoting it to the default planner. Feedback and bug reports are welcome via GitHub Issues.

---

## Reporting Issues

Found a bug or have a suggestion? [Open an issue](https://github.com/unrealandychan/rekipedia/issues/new/choose) and include:

- rekipedia version (`rekipedia --version`)
- Operating system + Python version
- Steps to reproduce
- Expected vs actual behaviour
