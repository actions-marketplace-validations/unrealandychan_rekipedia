---
slug: installation-and-setup
title: "Getting Started: Build and Run"
section: getting-started
tags: [getting-started, configuration]
pin: false
importance: 68
created_at: 2026-05-05T04:57:55Z
rekipedia_version: 0.10.3
---

# Getting Started: Build and Run

This page focuses on the shortest path to a successful local setup and a production-like run of the project. It deliberately avoids project overview and architecture details, and concentrates on prerequisites, installation, build commands, and a minimal verification step.

## Prerequisites

The repository contains explicit signals about the toolchain it expects in different distribution modes:

- **Python packaging/tooling** is present via `pyproject.toml`, `uv.lock`, and the package entry points declared in the evidence:
  - `rekipedia = "rekipedia.cli:main"`
  - `reki = "rekipedia.cli:main"`
- **Go toolchain** is also required for the Go implementation under `go/`, with build commands and a Go module file in `go/go.mod`.
- **Node/TypeScript tooling** is used for the TypeScript build path, indicated by `package.json` and the explicit build command `npm run build  # tsc`.
- **Docker** is supported for a containerized production-like build, with `docker build .` and a scratch-based Docker image in the evidence (`FROM scratch`).
- The repo also contains standard developer tooling and configuration files such as `.env.sample`, `.pre-commit-config.yaml`, `.eslintrc.json`, `.golangci.yml`, and `.prettierrc.json`, indicating linting and environment configuration are part of the expected workflow.

### Environment variables and configuration

The only explicitly evidenced environment/configuration artifact in the payload is [` .env.sample`](.env.sample), which strongly suggests copying or adapting it for local runs. The analysis payload does not expose the actual variable names, so the safest guidance is:

1. Start from `.env.sample`.
2. Populate values required by your chosen runtime path.
3. Keep any secrets or API keys local and uncommitted.

If you are following the Go runtime path, the codebase also includes LLM-related configuration types such as [`LLMConfig`](go/internal/models/contracts.go#L6) and a default configuration helper [`DefaultLLMConfig`](go/internal/models/contracts.go#L18), which indicates runtime behavior may depend on model/provider settings even if the exact env var names are not surfaced in the analysis.

> **Sources:** `.env.sample` · `pyproject.toml` · `uv.lock` · `go/go.mod` · `package.json` · `Dockerfile.sandbox` · [`LLMConfig`](go/internal/models/contracts.go#L6-L15) · [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23)

## Installation

There are at least two practical installation tracks visible in the repository: Python packaging for the `rekipedia` CLI, and a Go build path for the newer implementation under `go/`.

### Python path

The Python package is configured with console entry points in the repository evidence:

```text
rekipedia = "rekipedia.cli:main"
reki = "rekipedia.cli:main"
```

That means a successful installation should expose either `rekipedia` or `reki` on your PATH. The packaging toolchain is centered around **uv** and **hatch** based on the build commands found in the repo.

Typical local workflow:

```bash
uv sync
uv build
```

If you prefer the hatch workflow:

```bash
hatch build
```

### Go path

The Go project lives under `go/` and has its own module and build tooling. A minimal build from that subdirectory is:

```bash
cd go
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

This produces a statically linked binary-like artifact suitable for local testing or containerization.

> **Sources:** `pyproject.toml` · `uv.lock` · `go/go.mod` · `go/cmd/rekipedia/main.go` · `go/cmd/rekipedia/cmd/root.go` · `go/cmd/rekipedia/cmd/serve.go` · `go/Makefile`

## Supported build commands

The repository evidence explicitly names the following build commands:

| Command | Use case | Notes |
|--------|----------|-------|
| `uv build` | Python package build | Matches the Python packaging workflow |
| `hatch build` | Python package build | Appears twice in evidence, likely an alternate or repeated CI target |
| `CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia` | Go binary build | Produces a stripped, statically linked binary |
| `docker build .` | Container image build | Production-like image build path |
| `npm run build  # tsc` | TypeScript compilation | Uses the project’s npm/TypeScript toolchain |

A few practical observations from the evidence:

- `CGO_ENABLED=0` is an explicit requirement for the Go binary build command.
- `-ldflags "-s -w"` indicates the Go binary is intended to be minimized for distribution.
- `docker build .` pairs naturally with the `FROM scratch` evidence, implying a very small runtime image.
- The TypeScript path is explicitly compile-only (`tsc`), which is consistent with build-time verification rather than a runtime server.

> **Sources:** `Makefile` · `go/Makefile` · `package.json` · `go/Dockerfile` · `Dockerfile.sandbox`

## Local development workflow

For day-to-day development, the fastest path is usually to build from the language/runtime you are actively changing.

### Python development loop

If you are working on the Python CLI or library code under `src/rekipedia/`, use the Python packaging toolchain:

```bash
uv sync
uv build
```

If your environment is already configured with hatch:

```bash
hatch build
```

The repository also exposes a CLI entry point from Python, so after installation you should be able to run:

```bash
rekipedia --help
# or
reki --help
```

### Go development loop

For the Go implementation, the primary build target is the command under `go/cmd/rekipedia`:

```bash
cd go
go build ./cmd/rekipedia
```

For a production-like artifact, prefer the explicit stripped build used in the evidence:

```bash
cd go
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

The command tree under `go/cmd/rekipedia/` includes subcommands like `serve`, `scan`, `update`, `export`, and `watch`, with the CLI rooted in [`main`](go/cmd/rekipedia/main.go#L6-L8) and dispatched through [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48).

> **Sources:** `src/rekipedia/__main__.py` · `src/rekipedia/cli/__init__.py` · `go/cmd/rekipedia/main.go` · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48) · `go/cmd/rekipedia/cmd/root.go` · `go/cmd/rekipedia/cmd/serve.go` · `go/cmd/rekipedia/cmd/watch.go`

## Production-like modes

The repository supports more than one “production-like” execution pattern.

### Containerized run

The clearest production-style path is Docker-based:

```bash
docker build .
```

This is reinforced by the scratch-based base image evidence (`FROM scratch`), which suggests the final image is designed for a minimal runtime footprint.

### Compiled binary run

For a non-containerized production-like artifact, build the Go CLI with CGO disabled:

```bash
cd go
CGO_ENABLED=0 go build -ldflags "-s -w" -o reki ./cmd/rekipedia
./reki --help
```

This is likely the closest local approximation to how the CLI would be shipped or embedded in release artifacts.

### TypeScript validation build

If you are working on the TS frontend or helper package, the production-like step is the TypeScript compile:

```bash
npm run build  # tsc
```

That command is a build-time verification, not a runtime start command, but it is still an important “first success” milestone for the JS/TS path.

> **Sources:** `go/Dockerfile` · `Dockerfile.sandbox` · `go/cmd/rekipedia/main.go` · `package.json`

## Minimal verification step

The minimal verification step should prove that the toolchain is installed, the project builds, and the CLI can start or at least report its usage.

### Recommended smoke tests

Pick one based on the code path you are using:

#### Go CLI smoke test

```bash
cd go
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
/tmp/reki --help
```

Success criteria:
- the binary builds without errors
- the binary prints CLI usage/help
- no missing dependency or runtime configuration errors appear immediately

#### Python CLI smoke test

```bash
uv build
rekipedia --help
```

or, if the installed binary is named differently:

```bash
reki --help
```

Success criteria:
- the package builds
- the console script launches
- help text renders without stack traces

#### Docker smoke test

```bash
docker build .
```

Success criteria:
- the image builds successfully
- no missing build context or dependency issues are reported

### What not to over-validate here

This page is intentionally not the place to verify graph generation, wiki export, or orchestration features. The goal is only to confirm that setup is correct and the project can be built/run in at least one supported mode.

> **Sources:** `go/cmd/rekipedia/main.go` · `go/cmd/rekipedia/cmd/root.go` · `pyproject.toml` · `package.json` · `go/Dockerfile`