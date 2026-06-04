# ADR 0001: Go Port Charter

**Date:** 2026-06-02
**Status:** Proposed

---

## Context

rekipedia began as a Python project (`src/rekipedia/`). A Go port was later developed to provide a self-contained binary distribution that requires no Python runtime. The Go implementation lives under `go/` and covers the same high-level pipeline: repository scanning, symbol extraction, wiki synthesis, embedding, RAG search, and a web server.

As both implementations have grown, contributors have asked:

- Which implementation should be used in production?
- Are the two implementations expected to stay in sync?
- What is the strategic direction for the Go port — will it eventually replace Python?

Without a documented answer, contributors risk duplicating effort, making incompatible changes, or misrepresenting the Go port's maturity to users.

---

## Decision

1. **Python (`src/rekipedia/`) is the canonical, primary implementation.** It is the reference for correctness and receives new features first. Production users and integrators should default to the Python package.

2. **The Go port is an experimental, high-performance alternative.** It is *not* a drop-in replacement. The CLI surface is broadly compatible, but internal behaviour, configuration schema, and edge-case handling may diverge.

3. **Feature parity is not currently required.** The Go port tracks Python features on a best-effort basis. New language support, heuristics, or LLM prompt changes are implemented in Python first; Go maintainers may port them when capacity allows.

4. **The long-term role of the Go port is an open question.** No decision is made at this time about whether Go will eventually become co-primary, be scoped to a read-only subset of commands, or be deprecated. This ADR will be superseded when a directional decision is reached.

---

## Consequences

### Positive

- Users and contributors have a clear, authoritative reference implementation.
- The Go port can evolve at its own pace without blocking Python feature development.
- The project can honestly communicate the experimental status of the Go port, reducing support burden.

### Negative / Trade-offs

- Maintaining two implementations imposes ongoing overhead.
- Users who adopt the Go port in production accept that it may lag behind or diverge from Python behaviour.
- Leaving the long-term direction open risks stagnation; a follow-up ADR should be filed once enough data exists to make a directional call.

### Neutral

- Existing Go port users are unaffected; no behaviour changes are made by this ADR.
- The Go port continues to be released and distributed as before.
