---
slug: installation-and-setup
title: "Getting Started: Install and Build"
section: getting-started
tags: [getting-started, configuration]
pin: false
importance: 50
created_at: 2026-05-05T04:24:46Z
rekipedia_version: 0.10.2
---

# Getting Started: Install and Build

This page documents the repository-provided installation and build paths for the supported environments: Python, Go, JavaScript/Node, and container-based builds. It is intentionally limited to commands and configuration files that exist in the repository, and it focuses on build-time setup and validation only.

## Prerequisites

The repository contains evidence of four build ecosystems:

- Python packaging via [`pyproject.toml`](pyproject.toml) and lockfile [`uv.lock`](uv.lock)
- Go module builds via [`go/go.mod`](go/go.mod) and [`go/Makefile`](go/Makefile)
- JavaScript/Node tooling via [`package.json`](package.json)
- Container builds via [`Dockerfile.sandbox`](Dockerfile.sandbox) and [`go/Dockerfile`](go/Dockerfile)

There is also repository configuration that commonly affects installation and build reproducibility:

| File | Purpose |
|------|---------|
| [`pyproject.toml`](pyproject.toml) | Python project metadata and build configuration |
| [`uv.lock`](uv.lock) | Locked Python dependency resolution |
| [`package.json`](package.json) | Node package scripts and dependencies |
| [`go/go.mod`](go/go.mod) | Go module definition |
| [`go/Makefile`](go/Makefile) | Go build entry points and convenience targets |
| [`Makefile`](Makefile) | Top-level repository automation |
| [`.env.sample`](.env.sample) | Example environment configuration |
| [`.golangci.yml`](.golangci.yml) | Go lint configuration |
| [`.eslintrc.json`](.eslintrc.json) | JavaScript lint configuration |
| [`.prettierrc.json`](.prettierrc.json) | JavaScript formatting configuration |
| [`.pre-commit-config.yaml`](.pre-commit-config.yaml) | Git hook automation and local checks |
| [`Dockerfile.sandbox`](Dockerfile.sandbox) | Container image for sandboxed execution |
| [`go/Dockerfile`](go/Dockerfile) | Go-focused container build |

A good first validation step is to inspect the project’s top-level build files and choose the environment you want to use. The repository’s build commands are summarized in later sections.

> **Sources:** `pyproject.toml` · `uv.lock` · `package.json` · `go/go.mod` · `go/Makefile` · `Makefile` · `.env.sample` · `.golangci.yml` · `.eslintrc.json` · `.prettierrc.json` · `.pre-commit-config.yaml` · `Dockerfile.sandbox` · `go/Dockerfile`

## Python Environment

The Python build path is defined by [`pyproject.toml`](pyproject.toml) and the pinned lockfile [`uv.lock`](uv.lock). The analysis data also shows a Python package layout under [`src/rekipedia`](src/rekipedia/__init__.py), which is consistent with a standard source-layout project. The repository-provided build command for Python is:

```bash
uv build
```

This is the most direct Python packaging command in the repository data. It is appropriate when you want to validate that the Python project can be packaged successfully using the locked dependency set.

A second Python-oriented build command appears in the repository build command list:

```bash
hatch build
```

Because `hatch build` appears in the repository-provided commands, it should be treated as an alternate packaging route, likely used by maintainers who prefer Hatch-based workflows. The repository data does not show a separate Hatch configuration file in the file list, so the safest assumption is that this is a supported command only if your local environment already has Hatch available and the project metadata is compatible.

### Validation Expectations

A successful Python build should produce distributable artifacts, typically in a local build directory. The exact filenames are not enumerated in the analysis data, so the build should be treated as successful when it completes without error and emits package artifacts consistent with the tool in use.

### Caveats

- Prefer `uv build` if you are following the pinned Python dependency path from [`uv.lock`](uv.lock).
- `hatch build` is present in the command inventory, but no dedicated Hatch config file is visible in the repository snapshot.
- This page does not describe runtime or application startup behavior; use build completion as the validation point.

> **Sources:** `pyproject.toml` · `uv.lock` · `src/rekipedia/__init__.py` · `src/rekipedia/__main__.py`

## Go Build

The Go project is rooted in [`go/go.mod`](go/go.mod) and uses the command package under [`go/cmd/rekipedia`](go/cmd/rekipedia). The repository-provided build command is:

```bash
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

This command is the clearest build invocation in the analysis data. It disables CGO, strips symbol/debug information, and writes the resulting binary to `/tmp/reki`. That makes it suitable for producing a compact standalone executable during local verification or release-style builds.

The Go tree also includes a dedicated [`go/Makefile`](go/Makefile), which suggests additional wrapper targets exist for maintainers working inside the Go subdirectory. However, because the actual target names are not included in the analysis data, the only command we can document with certainty is the direct `go build` invocation above.

### Validation Expectations

When this build succeeds, the expected output is a compiled Go binary at `/tmp/reki`. A successful build validates that the module resolves, compiles, and links correctly under the repository’s Go toolchain expectations.

### Caveats

- `CGO_ENABLED=0` means the build is intentionally static-CGO-free.
- The binary output path is temporary and may not be appropriate for long-term use.
- The repository data does not include a versioned release script in this page’s scope, so use the direct build command for validation.

> **Sources:** `go/go.mod` · `go/Makefile` · `go/cmd/rekipedia/main.go` · `go/cmd/rekipedia/cmd/root.go`

## JavaScript/Node Build

The Node/JavaScript build path is supported by [`package.json`](package.json), with formatting and linting governed by [`.eslintrc.json`](.eslintrc.json) and [`.prettierrc.json`](.prettierrc.json). The repository-provided build command is:

```bash
npm run build  # tsc
```

The inline comment in the build command inventory indicates that this script invokes TypeScript compilation (`tsc`). That means the main build validation for the Node environment is a compile step rather than a runtime test.

The repository also contains `bin/rekipedia.js`, which is a JavaScript entry point file, but the task here is limited to installation/build validation rather than CLI behavior. So the build command should be treated as a compile-time check for the JavaScript/TypeScript toolchain.

### Validation Expectations

A successful Node build should complete the TypeScript compilation step without errors. The precise output files are not listed in the analysis data, so build success is defined by a clean exit from the script.

### Caveats

- The build command is tied to the package scripts in [`package.json`](package.json).
- Lint and formatting are configured separately through `.eslintrc.json` and `.prettierrc.json`, but they are not build commands.
- The analysis data only confirms `npm run build` as the documented build entry point; it does not enumerate additional scripts.

> **Sources:** `package.json` · `.eslintrc.json` · `.prettierrc.json` · `bin/rekipedia.js`

## Container Build

The repository includes two Dockerfiles: [`Dockerfile.sandbox`](Dockerfile.sandbox) and [`go/Dockerfile`](go/Dockerfile). The analysis data also lists a container build command:

```bash
docker build .
```

This is the documented top-level container build invocation. It is the right choice when you want to validate that the repository can be built in a containerized environment without relying on a preinstalled local language toolchain.

Because the analysis data includes both a general Dockerfile at the repository root and a Go-specific Dockerfile inside `go/`, there are at least two container build contexts in the repository. However, only `docker build .` is listed in the build-command inventory, so that is the only container build command we should recommend here without guessing about tags, targets, or alternate build arguments.

### Validation Expectations

A successful container build should produce a local Docker image. The image name and tag are not specified in the analysis data, so validation is simply that the Docker build completes successfully.

### Caveats

- The command as listed uses the repository root as the build context.
- If you are targeting the Go subproject specifically, the presence of [`go/Dockerfile`](go/Dockerfile) suggests a separate containerization path may exist, but it is not captured as a documented command here.
- Container builds can depend on your local Docker daemon, network access, and base-image availability.

> **Sources:** `Dockerfile.sandbox` · `go/Dockerfile`

## Build Commands Reference

The following table summarizes the repository-provided build commands, when to use them, expected outputs, and important caveats.

| Command | When to use | Expected output | Caveats |
|--------|-------------|-----------------|----------|
| `uv build` | Python packaging validation using the locked Python dependency set | Local Python build artifacts/package distribution | Requires the Python toolchain used by `uv`; exact artifact names are not specified in the repository data |
| `hatch build` | Alternate Python packaging path for Hatch-based workflows | Local Python build artifacts/package distribution | No dedicated Hatch config file is visible in the provided file list |
| `CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia` | Build the Go binary directly and validate module compilation | Executable binary at `/tmp/reki` | Output path is temporary; CGO is disabled; build is scoped to `go/cmd/rekipedia` |
| `npm run build  # tsc` | Validate the JavaScript/TypeScript build | Successful TypeScript compilation | The command inventory only confirms the script name and `tsc` comment, not additional package scripts |
| `docker build .` | Validate the repository in a containerized build environment | Local Docker image | Uses the repository root as the build context; image tag/name not specified |

> **Sources:** `uv.lock` · `pyproject.toml` · `go/go.mod` · `go/cmd/rekipedia/main.go` · `package.json` · `Dockerfile.sandbox` · `go/Dockerfile`

## Recommended Local Workflow

A practical, repository-aligned workflow is to pick the build path that matches the environment you are maintaining:

1. Use `uv build` for the Python distribution path.
2. Use `CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia` for the Go binary.
3. Use `npm run build  # tsc` for the JavaScript/TypeScript toolchain.
4. Use `docker build .` when you want a containerized verification.

If you are unsure which path is canonical for your use case, inspect the matching project files first: [`pyproject.toml`](pyproject.toml), [`go/go.mod`](go/go.mod), and [`package.json`](package.json).

> **Sources:** `pyproject.toml` · `go/go.mod` · `package.json` · `Dockerfile.sandbox` · `go/Dockerfile`