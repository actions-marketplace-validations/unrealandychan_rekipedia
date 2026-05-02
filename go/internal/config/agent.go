package config

import (
	"os"
	"path/filepath"
)

const agentContent = `# rekipedia — AI Codebase Intelligence

This repository uses [rekipedia](https://github.com/unrealandychan/rekipedia) to maintain a structured wiki and answer questions about the codebase.

## Available commands

| Command | What it does |
|---------|-------------|
| ` + "`" + `reki scan .` + "`" + ` | Full scan — extract symbols, generate wiki pages, build knowledge store |
| ` + "`" + `reki update .` + "`" + ` | Incremental refresh — only re-processes changed files |
| ` + "`" + `reki ask "<question>"` + "`" + ` | Ask anything about the codebase — grounded answers with file:line citations |
| ` + "`" + `reki serve .` + "`" + ` | Start local web UI at http://127.0.0.1:7070 to browse wiki & ask questions |
| ` + "`" + `reki embed .` + "`" + ` | Build / rebuild the semantic search index (FAISS) for hybrid RAG |
| ` + "`" + `reki export .` + "`" + ` | Export wiki to a single file (--format md|zip|json) |

## When to use rekipedia

- Before answering questions about the codebase architecture, run ` + "`" + `reki ask "<your question>"` + "`" + ` to get grounded context
- After making significant changes, run ` + "`" + `reki update .` + "`" + ` to keep the wiki current
- When asked to understand how a feature works, check the wiki first with ` + "`" + `reki ask` + "`" + `
- When onboarding to an unfamiliar part of the codebase, use ` + "`" + `reki ask` + "`" + ` for guided explanation

## Setup (first time)

` + "```" + `bash
reki scan .          # generates the wiki and knowledge store
reki embed .         # builds semantic search index (optional, for RAG)
` + "```" + `

The knowledge store lives in ` + "`.rekipedia/store.db`" + ` — portable, local, no cloud required.
`

// AgentFile describes a file to write and its display name.
type AgentFile struct {
	RelPath  string
	Platform string
}

var agentFiles = []AgentFile{
	{"CLAUDE.md", "Claude Code"},
	{"AGENTS.md", "Codex / OpenAI Agents"},
	{filepath.Join(".github", "copilot-instructions.md"), "GitHub Copilot"},
}

// WriteAgentFiles writes agent instruction files into repoRoot.
// Returns a slice of (path, created bool) for each file so callers can report status.
func WriteAgentFiles(repoRoot string, force bool) ([]AgentFileResult, error) {
	var results []AgentFileResult
	for _, af := range agentFiles {
		fullPath := filepath.Join(repoRoot, af.RelPath)
		_, err := os.Stat(fullPath)
		exists := err == nil
		if exists && !force {
			results = append(results, AgentFileResult{Path: fullPath, Platform: af.Platform, Created: false})
			continue
		}
		if err := os.MkdirAll(filepath.Dir(fullPath), 0o755); err != nil {
			return results, err
		}
		if err := os.WriteFile(fullPath, []byte(agentContent), 0o644); err != nil {
			return results, err
		}
		results = append(results, AgentFileResult{Path: fullPath, Platform: af.Platform, Created: true})
	}
	return results, nil
}

// AgentFileResult holds the outcome for a single agent file write.
type AgentFileResult struct {
	Path     string
	Platform string
	Created  bool
}
