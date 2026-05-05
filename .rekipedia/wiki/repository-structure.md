---
slug: repository-structure
title: "Repository Structure"
section: internals
tags: [repository-structure, internals]
pin: false
importance: 50
created_at: 2026-05-05T03:36:19Z
rekipedia_version: 0.10.1
---

# Repository Structure

## Overview

This document provides a comprehensive map of the repository structure, detailing the purpose and key files of each top-level directory. It also explains the layout of the `src`, `tests`, and configuration files, and includes a Mermaid diagram showing the dependencies between top-level packages.

## Annotated Directory Tree

```plaintext
.
├── .coverage
├── .editorconfig
├── .env.sample
├── .eslintrc.json
├── .gitignore
├── .golangci.yml
├── .mcp.json
├── .pre-commit-config.yaml
├── .prettierrc.json
├── AGENTS.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── Dockerfile.sandbox
├── LICENSE
├── Makefile
├── README.md
├── RELEASE-NOTES.md
├── checkstyle.xml
├── close-wiki-0.7.3.tgz
├── close-wiki-0.8.4.tgz
├── close-wiki-0.8.5.tgz
├── close-wiki-0.9.0.tgz
├── coverage.json
├── package.json
├── pmd-ruleset.xml
├── pyproject.toml
├── rekipedia-0.9.3.tgz
├── rekipedia-0.9.4.tgz
├── rekipedia-0.9.5.tgz
├── rekipedia-0.9.7.tgz
├── rekipedia-agent-skill.md
├── uv.lock
├── .github
│   ├── _rules.instructions.md
│   ├── clean-code-review.instructions.md
│   ├── copilot-instructions.md
│   ├── husky-enforcement.instructions.md
│   ├── lint-report.instructions.md
│   ├── scripts
│   │   └── update-homebrew-tap.py
│   ├── workflows
│   │   ├── go-ci.yml
│   │   ├── go-release.yml
│   │   ├── npm-publish.yml
│   │   ├── python-ci.yml
│   │   ├── python-release.yml
├── .pytest_cache
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   ├── README.md
│   ├── v/cache/lastfailed
│   ├── v/cache/nodeids
├── .ruff_cache
│   ├── .gitignore
│   ├── 0.15.8/15568880085755169911
│   ├── 0.15.8/16622096983324106815
│   ├── 0.15.8/4009862412007594282
│   ├── CACHEDIR.TAG
├── bin
│   └── rekipedia.js
├── docs
│   ├── PLAN.md
│   ├── customizing.md
│   ├── plans
│   │   ├── 2026-04-29-phase5-serve.md
│   │   ├── golang-rewrite.md
├── go
│   ├── .goreleaser.yaml
│   ├── Dockerfile
│   ├── Makefile
│   ├── README.md
│   ├── RELEASE-NOTES.md
│   ├── cmd
│   │   ├── rekipedia
│   │   │   ├── cmd
│   │   │   │   ├── ask.go
│   │   │   │   ├── context.go
│   │   │   │   ├── diff.go
│   │   │   │   ├── embed.go
│   │   │   │   ├── embed_export_update_test.go
│   │   │   │   ├── export.go
│   │   │   │   ├── hook.go
│   │   │   │   ├── hook_test.go
│   │   │   │   ├── impact.go
│   │   │   │   ├── init.go
│   │   │   │   ├── refactor.go
│   │   │   │   ├── refactor_test.go
│   │   │   │   ├── root.go
│   │   │   │   ├── root_test.go
│   │   │   │   ├── scan.go
│   │   │   │   ├── search.go
│   │   │   │   ├── serve.go
│   │   │   │   ├── update.go
│   │   │   │   ├── watch.go
│   │   │   ├── main.go
│   ├── go.mod
│   ├── go.sum
│   ├── install.sh
│   ├── internal
│   │   ├── analysis
│   │   │   ├── refactor_detector.go
│   │   │   ├── refactor_detector_test.go
│   │   │   ├── refactor_enricher.go
│   │   │   ├── refactor_enricher_test.go
│   │   │   ├── refactor_types.go
│   │   │   ├── refactor_writer.go
│   │   │   ├── refactor_writer_test.go
│   │   ├── config
│   │   │   ├── agent.go
│   │   │   ├── loader.go
│   │   │   ├── loader_test.go
│   │   ├── exporter
│   │   │   ├── exporter_test.go
│   │   │   ├── json_exporter.go
│   │   │   ├── markdown_exporter.go
│   │   ├── extractor
│   │   │   ├── config.go
│   │   │   ├── extractor.go
│   │   │   ├── extractor_test.go
│   │   │   ├── golang.go
│   │   │   ├── python.go
│   │   │   ├── typescript.go
│   │   ├── graph
│   │   │   ├── graph_analysis.go
│   │   │   ├── graph_analysis_test.go
│   │   │   ├── hub_gap_test.go
│   │   ├── llm
│   │   │   ├── client.go
│   │   │   ├── client_test.go
│   │   ├── models
│   │   │   ├── contracts.go
│   │   │   ├── contracts_test.go
│   │   ├── orchestrator
│   │   │   ├── helpers.go
│   │   │   ├── orchestrator_test.go
│   │   │   ├── run_ask.go
│   │   │   ├── run_digest.go
│   │   │   ├── run_update.go
│   │   │   ├── sharding.go
│   │   │   ├── snapshotter.go
│   │   ├── rag
│   │   │   ├── chunker.go
│   │   │   ├── embedder.go
│   │   │   ├── rag_test.go
│   │   │   ├── scan_meta.go
│   │   │   ├── vector_store.go
│   │   ├── server
│   │   │   ├── server.go
│   │   │   ├── server_test.go
│   │   │   ├── templates
│   │   │   │   ├── ask.html
│   │   │   │   ├── base.html
│   │   │   │   ├── graph.html
│   │   │   │   ├── index.html
│   │   │   │   ├── wiki.html
│   │   ├── storage
│   │   │   ├── aliases.go
│   │   │   ├── store.go
│   │   │   ├── store_test.go
│   │   ├── synthesis
│   │   │   ├── diagram_builder.go
│   │   │   ├── page_builder.go
│   │   │   ├── planner.go
│   │   │   ├── synthesis_test.go
│   │   ├── pkg
│   │   │   ├── fsutil
│   │   │   │   ├── walk.go
│   │   │   │   ├── walk_test.go
├── htmlcov
│   ├── .gitignore
│   ├── class_index.html
│   ├── coverage_html_cb_dd2e7eb5.js
│   ├── favicon_32_cb_c827f16f.png
│   ├── function_index.html
│   ├── index.html
│   ├── keybd_closed_cb_900cfef5.png
│   ├── status.json
│   ├── style_cb_9ff733b0.css
│   ├── z_0ae714acd8f88e56___init___py.html
│   ├── z_0ae714acd8f88e56_client_py.html
│   ├── z_1136fd4e7e454593___init___py.html
│   ├── z_1136fd4e7e454593_json_export_py.html
│   ├── z_1136fd4e7e454593_markdown_export_py.html
│   ├── z_17cf55344efb66e6___init___py.html
│   ├── z_17cf55344efb66e6_ask_py.html
│   ├── z_17cf55344efb66e6_init_py.html
│   ├── z_17cf55344efb66e6_scan_py.html
│   ├── z_17cf55344efb66e6_update_py.html
│   ├── z_38f53f4c2a135f0c___init___py.html
│   ├── z_38f53f4c2a135f0c_runner_py.html
│   ├── z_61b981ff590e613f___init___py.html
│   ├── z_61b981ff590e613f_analyze_shard_py.html
│   ├── z_71ca1a681c588863___init___py.html
│   ├── z_71ca1a681c588863___main___py.html
│   ├── z_7aefebc73fb285f1___init___py.html
│   ├── z_7aefebc73fb285f1_sqlite_store_py.html
│   ├── z_842b6b92605fd8fd___init___py.html
│   ├── z_842b6b92605fd8fd_base_py.html
│   ├── z_842b6b92605fd8fd_config_extractor_py.html
│   ├── z_842b6b92605fd8fd_python_extractor_py.html
│   ├── z_842b6b92605fd8fd_typescript_extractor_py.html
│   ├── z_9a57c7756e01d46b___init___py.html
│   ├── z_9a57c7756e01d46b_diagram_builder_py.html
│   ├── z_9a57c7756e01d46b_page_builder_py.html
│   ├── z_a1c4734f5d66c750___init___py.html
│   ├── z_a1c4734f5d66c750_contracts_py.html
│   ├── z_cfd03fba86859063___init___py.html
│   ├── z_cfd03fba86859063_run_ask_py.html
│   ├── z_cfd03fba86859063_run_digest_py.html
│   ├── z_cfd03fba86859063_run_update_py.html
│   ├── z_cfd03fba86859063_sharding_py.html
│   ├── z_cfd03fba86859063_snapshotter_py.html
├── pipelines
│   ├── harness-canary.yaml
│   ├── harness-ci.yaml
│   ├── harness-feature-flag-gate.yaml
├── schemas
│   └── analysis_result.schema.json
├── scripts
│   └── lint-and-report.sh
├── skills
│   ├── harness
│   │   ├── observability.md
│   │   ├── progressive-delivery.md
│   │   ├── testability.md
│   ├── shared
│   │   ├── harness-rules.md
│   │   ├── husky-rules.md
│   │   ├── lint-report-prompt.md
│   │   ├── observability-report-prompt.md
│   │   ├── rules.md
│   │   ├── test-review-prompt.md
├── src
│   ├── rekipedia
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── analysis
│   │   │   ├── __init__.py
│   │   │   ├── cross_repo_search.py
│   │   │   ├── graph_analysis.py
│   │   │   ├── graph_export.py
│   │   │   ├── impact.py
│   │   │   ├── refactor_detector.py
│   │   │   ├── refactor_enricher.py
│   │   │   ├── refactor_writer.py
│   │   ├── cli
│   │   │   ├── __init__.py
│   │   │   ├── ask.py
│   │   │   ├── context.py
│   │   │   ├── diff.py
│   │   │   ├── embed.py
│   │   │   ├── export.py
│   │   │   ├── hook.py
│   │   │   ├── impact.py
│   │   │   ├── init.py
│   │   │   ├── mcp_cmd.py
│   │   │   ├── mcp_server.py
│   │   │   ├── refactor.py
│   │   │   ├── scan.py
│   │   │   ├── search.py
│   │   │   ├── serve.py
│   │   │   ├── update.py
│   │   │   ├── watch.py
│   │   ├── exporters
│   │   │   ├── __init__.py
│   │   │   ├── json_export.py
│   │   │   ├── markdown_export.py
│   │   ├── extractors
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── config_extractor.py
│   │   │   ├── go_extractor.py
│   │   │   ├── java_extractor.py
│   │   │   ├── python_extractor.py
│   │   │   ├── rust_extractor.py
│   │   │   ├── typescript_extractor.py
│   │   ├── llm
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   ├── models
│   │   │   ├── __init__.py
│   │   │   ├── contracts.py
│   │   ├── orchestrator
│   │   │   ├── __init__.py
│   │   │   ├── agent_hints.py
│   │   │   ├── run_ask.py
│   │   │   ├── run_digest.py
│   │   │   ├── run_update.py
│   │   │   ├── sharding.py
│   │   │   ├── snapshot.py
│   │   │   ├── snapshotter.py
│   │   ├── prompts
│   │   │   ├── ask_system.md
│   │   │   ├── digest_system.md
│   │   ├── rag
│   │   │   ├── __init__.py
│   │   │   ├── embedder.py
│   │   │   ├── scan_meta.py
│   │   ├── sandbox
│   │   │   ├── __init__.py
│   │   │   ├── runner.py
│   │   │   ├── tasks
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analyze_shard.py
│   │   ├── server
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── templates
│   │   │   │   ├── ask.html
│   │   │   │   ├── base.html
│   │   │   │   ├── graph.html
│   │   │   │   ├── index.html
│   │   │   │   ├── wiki.html
│   │   ├── storage
│   │   │   ├── __init__.py
│   │   │   ├── migrations
│   │   │   │   ├── 001_initial.sql
│   │   │   │   ├── 002_qa_history.sql
│   │   │   ├── sqlite_store.py
│   │   ├── synthesis
│   │   │   ├── __