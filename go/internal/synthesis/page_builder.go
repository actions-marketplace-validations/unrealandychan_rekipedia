// Package synthesis — PageBuilder generates wiki page content via LLM.
package synthesis

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	"golang.org/x/sync/errgroup"

	"github.com/unrealandychan/rekipedia/internal/llm"
	"github.com/unrealandychan/rekipedia/internal/models"
)

const pageSystemPrompt = `You are an expert software architect, tech lead, and technical writer AI.
Your job is to analyse a software repository and produce thorough, deeply detailed wiki documentation.

You will be given:
- A JSON payload with static analysis data (files, symbols, relationships, cross_module_summary, build/test commands, risks, evidence)
- A specific Task describing which wiki page to write and what to focus on

## Output Format
Produce rich Markdown (NOT JSON). Your output is written directly to a .md file.
Requirements:
- Start with a single # Page Title heading
- Use ## Section and ### Subsection headings liberally
- Every section must have real, substantive content — no one-liners, no placeholder text
- Reference actual symbol names, file paths, function signatures from the analysis data
- Include Mermaid diagrams where relevant (architecture, data flow, module relationships, call graphs)
- Use code blocks for commands, config examples, and code snippets
- Use tables where comparing options, listing commands, or summarising properties
- Minimum ~400 words per page; complex pages should be 800-1200 words
- Write in clear, professional English suitable for a developer audience

## Mermaid Diagram Rules
- Use flowchart TD or flowchart LR for component/data-flow diagrams
- Use classDiagram for class hierarchies
- Use sequenceDiagram for request/response flows
- Node IDs: only [A-Za-z0-9_] — no spaces, dots, slashes
- Limit to the 15 most important nodes/edges per diagram
- Always wrap in a fenced code block with mermaid language tag

## Cross-Module Relationship Rules (MANDATORY)
Every page covering modules or architecture MUST include:
- A cross-module dependency table: | Module | Imports From | Called By | Calls Into | Inherits From |
- Use the cross_module_summary field — it is pre-computed and accurate
- The architecture page MUST include a Mermaid flowchart LR of all major module-to-module imports
- The core-modules page MUST document for each module: what it imports, what imports it, what it calls, what calls it
- For important code paths, trace the full call chain: entrypoint -> moduleA.func -> moduleB.func

## Source Citation Rules (MANDATORY)
Whenever you mention a class, function, or module that exists in the symbols data, add an inline link:
` + "[`SymbolName`](relative/path/to/file.go#Lline_start)" + `
At the end of every ## section referencing symbols, add:
> **Sources:** ` + "`path/to/file.go`" + ` · L12-L45 · [` + "`ClassName`" + `](path/to/file.go#L12)

## Quality Rules
- Do NOT invent symbols, files, or behaviours not evidenced in the analysis data
- If analysis data is sparse for a section, acknowledge the gap honestly
- Do NOT output JSON — output Markdown only
- Do NOT include YAML frontmatter — that is added automatically
- Do NOT add markdown fences around the entire response`

// pageExtraFocus holds additional per-slug focus instructions injected into the prompt.
var pageExtraFocus = map[string]string{
	"architecture": `Write a deep architectural overview. Include:
## System Architecture
If a pre-built module graph is provided in the analysis data under diagrams["module-graph"], embed it EXACTLY as-is in a mermaid code block. Otherwise generate your own flowchart TD diagram.
## Component Breakdown
For each major component: what it does, its responsibilities, and which files implement it. Cite each file using inline source links e.g. [ComponentName](path/to/file.go#L1).
## Entry Points
List all entry points from entry_points data. For each one: what triggers it, what it does, and inline source link.
## Data Flow
Step-by-step description of how data moves through the system. Use a Mermaid sequence or flowchart diagram.
## Key Design Decisions
Notable patterns used (e.g. plugin architecture, event-driven, pipeline). Reference actual code evidence with source citations.
## Inter-Module Dependencies
Describe the major import relationships between packages.
## Cross-Module Dependency Map
Using cross_module_summary from the analysis data, generate a complete Mermaid flowchart LR showing ALL internal module-to-module import and call relationships. Then produce the cross-module table:
| Module | Imports From | Calls Into | Inherited By |
|--------|-------------|------------|-------------|
This section is MANDATORY — do not skip it even if data is sparse.
## Module Coupling Analysis
Identify tightly coupled pairs (high bidirectional deps) and isolated modules. Flag circular imports if any.`,

	"core-modules": `Document every significant module/package. For each one:
### Module Name (path/to/module)
- **Purpose**: what this module does
- **Public API**: list key exported classes and functions with their signatures
- **Key Classes**: brief description of each class, its constructor, and main methods
- **Key Functions**: signature + one-line description
- **Imports From**: list every internal module this module imports (from cross_module_summary[module].imports)
- **Imported By**: list every internal module that imports this one (from cross_module_summary[module].imported_by)
- **Calls**: key functions this module calls in other modules
- **Called By**: key functions in other modules that call into this module
- **Coupling Score**: high/medium/low based on total in+out edges
Include a Mermaid classDiagram showing class hierarchies if applicable.
At the end of the core-modules page, include a summary cross-module dependency table covering ALL documented modules.`,

	"algorithms": `Document the core algorithms and data processing logic. Include:
## Overview
What computational problems does this project solve?
## Algorithm Descriptions
For each significant algorithm or processing pipeline found in the symbols:
### Algorithm / Pipeline Name
- **Input**: what data it receives
- **Steps**: numbered list of processing steps
- **Output**: what it produces
- **Complexity**: time/space if discernible from the code
- **Code Reference**: file and function name
## Cross-Module Call Chains
Show how the most important algorithms span across modules:
entrypoint -> moduleA.function -> moduleB.function -> moduleC.function
Use a Mermaid sequenceDiagram for complex multi-module flows.
## Data Structures
Key data structures (classes, types, schemas) used internally — use a table or class diagram.
## Processing Pipeline
Mermaid flowchart of the main processing pipeline end-to-end.`,

	"cli-and-api": `Document all CLI commands and programmatic APIs. Include:
## CLI Reference
For each CLI command/subcommand found:
### command-name
| Option | Type | Default | Description |
|--------|------|---------|-------------|
List all flags and arguments. Show a usage example.
## Programmatic API
For each public class/function intended for external use:
### ClassName / function_name
- Signature
- Parameters table
- Return value
- Example usage (code block)
## Integration Examples
Show how to use the CLI and API together in a realistic workflow.
## Cross-Module Call Chain
Trace the full call chain from CLI entry point through all modules to the final output.`,

	"technical-debt": `Analyse and document all technical debt found in this codebase. Include:
## Summary
A 2–3 sentence executive summary of the overall technical health. Give an overall debt rating: Low / Medium / High / Critical.
## Debt Inventory
A prioritised table:
| # | Area | Severity | Description | Files Affected | Effort to Fix |
|---|------|----------|-------------|----------------|---------------|
Severity: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low. Effort: S (<1d) / M (1-3d) / L (1-2w) / XL (>2w).
## Critical Issues
For each Critical/High item: file references, the problematic pattern, why it matters, and a concrete fix suggestion.
## Code Smell Patterns
Recurring anti-patterns (God classes, deep nesting, duplicated logic, missing error handling, hardcoded values). Show a real example and recommended refactor.
## Missing Tests
Areas with insufficient coverage. List specific modules/functions lacking tests.
## Dependency & Security Concerns
Outdated or risky dependencies from go.mod / pyproject.toml / package.json.
## TODO / FIXME Tracker
Every TODO, FIXME, HACK, XXX comment found:
| File | Comment | Suggested Action |
|------|---------|-----------------|
## Refactoring Roadmap
| Priority | Action | Rationale | Estimated Effort |
|----------|--------|-----------|-----------------|
Do NOT fabricate issues — only report what is evidenced in the provided data.`,
}

const maxPageWorkers = 4

// PageBuilder builds wiki pages concurrently via the LLM.
type PageBuilder struct {
	client llm.Caller
}

// NewPageBuilder creates a PageBuilder backed by the given LLM client.
func NewPageBuilder(client llm.Caller) *PageBuilder {
	return &PageBuilder{client: client}
}

// BuildAll generates content for all pages in the plan concurrently.
// Returns map[slug]content.
func (b *PageBuilder) BuildAll(ctx context.Context, plan models.WikiPlan, result models.AnalysisResult, diagrams map[string][2]string) (map[string]string, error) {
	payload := buildPayload(result, diagrams)

	// Semaphore: max maxPageWorkers concurrent LLM calls
	type result_ struct {
		slug    string
		content string
	}
	resultCh := make(chan result_, len(plan.Pages))

	sem := make(chan struct{}, maxPageWorkers)
	eg, ctx := errgroup.WithContext(ctx)

	for _, spec := range plan.Pages {
		spec := spec // capture
		eg.Go(func() error {
			sem <- struct{}{}
			defer func() { <-sem }()

			content, err := b.BuildPage(ctx, spec, payload)
			if err != nil {
				// Don't fail the whole run — use a placeholder
				content = fmt.Sprintf("*Page generation failed: %v*\n", err)
			}
			resultCh <- result_{slug: spec.Slug, content: content}
			return nil
		})
	}

	if err := eg.Wait(); err != nil {
		return nil, err
	}
	close(resultCh)

	pages := make(map[string]string)
	for r := range resultCh {
		pages[r.slug] = r.content
	}
	return pages, nil
}

// BuildPage generates content for a single wiki page.
func (b *PageBuilder) BuildPage(ctx context.Context, spec models.WikiPageSpec, payload map[string]any) (string, error) {
	sliced := slicePayload(payload, spec.RequiredData)
	payloadJSON, _ := json.Marshal(sliced)

	focus := spec.Focus
	if extra, ok := pageExtraFocus[spec.Slug]; ok {
		focus = extra + "\n\n" + focus
	}

	prompt := fmt.Sprintf(
		"## Page to write\nSlug: %s\nTitle: %s\nSection: %s\nImportance: %d\n\nFocus instructions:\n%s\n\n## Repository data\n\n```json\n%s\n```",
		spec.Slug, spec.Title, spec.Section, spec.Importance, focus, string(payloadJSON),
	)

	content, err := b.client.Call(ctx, pageSystemPrompt, prompt)
	if err != nil {
		return "", fmt.Errorf("build page %q: %w", spec.Slug, err)
	}
	content = strings.TrimSpace(content)
	content = ensureFrontmatter(spec, content)
	return content, nil
}

// ── payload construction ──────────────────────────────────────────────────────

// buildPayload creates the full repository data payload for page generation.
func buildPayload(result models.AnalysisResult, diagrams map[string][2]string) map[string]any {
	// Symbol table: group by kind
	symbolTable := make(map[string][]map[string]any)
	for _, sym := range result.Symbols {
		kind := string(sym.Kind)
		symbolTable[kind] = append(symbolTable[kind], map[string]any{
			"name":      sym.Name,
			"file":      sym.File,
			"line":      sym.LineStart,
			"signature": sym.Signature,
			"docstring": sym.Docstring,
		})
	}

	// Top symbols sample (max 100)
	topSymbols := make([]map[string]any, 0, 100)
	for _, sym := range result.Symbols {
		if len(topSymbols) >= 100 {
			break
		}
		topSymbols = append(topSymbols, map[string]any{
			"name": sym.Name,
			"kind": string(sym.Kind),
			"file": sym.File,
			"line": sym.LineStart,
		})
	}

	// Relationship summary (increased limit to 1500)
	relLimit := 1500
	if len(result.Relationships) < relLimit {
		relLimit = len(result.Relationships)
	}
	relSummary := make([]map[string]any, 0, relLimit)
	for i, rel := range result.Relationships {
		if i >= relLimit {
			break
		}
		relSummary = append(relSummary, map[string]any{
			"from_": rel.From, "to": rel.To, "kind": string(rel.Kind),
		})
	}

	// Relationship stats by kind
	relByKind := make(map[string]int)
	for _, rel := range result.Relationships {
		k := string(rel.Kind)
		relByKind[k]++
	}
	relationshipStats := map[string]any{
		"total":   len(result.Relationships),
		"by_kind": relByKind,
	}

	// Cross-module summary: group by from_ -> kind -> []to
	type modEntry struct {
		Imports    []string
		ImportedBy []string
		Calls      []string
		CalledBy   []string
		Inherits   []string
		InheritedBy []string
	}
	crossModMap := make(map[string]*modEntry)
	ensureEntry := func(name string) {
		if _, ok := crossModMap[name]; !ok {
			crossModMap[name] = &modEntry{}
		}
	}
	contains := func(sl []string, s string) bool {
		for _, v := range sl {
			if v == s {
				return true
			}
		}
		return false
	}
	for _, rel := range result.Relationships {
		from := rel.From
		to := rel.To
		kind := string(rel.Kind)
		if from == "" || to == "" {
			continue
		}
		ensureEntry(from)
		ensureEntry(to)
		switch kind {
		case "import", "imports":
			if !contains(crossModMap[from].Imports, to) {
				crossModMap[from].Imports = append(crossModMap[from].Imports, to)
			}
			if !contains(crossModMap[to].ImportedBy, from) {
				crossModMap[to].ImportedBy = append(crossModMap[to].ImportedBy, from)
			}
		case "calls":
			if !contains(crossModMap[from].Calls, to) {
				crossModMap[from].Calls = append(crossModMap[from].Calls, to)
			}
			if !contains(crossModMap[to].CalledBy, from) {
				crossModMap[to].CalledBy = append(crossModMap[to].CalledBy, from)
			}
		case "inherits":
			if !contains(crossModMap[from].Inherits, to) {
				crossModMap[from].Inherits = append(crossModMap[from].Inherits, to)
			}
			if !contains(crossModMap[to].InheritedBy, from) {
				crossModMap[to].InheritedBy = append(crossModMap[to].InheritedBy, from)
			}
		}
	}
	// Score and limit to top 100
	type scoredMod struct {
		name  string
		entry *modEntry
		score int
	}
	scored := make([]scoredMod, 0, len(crossModMap))
	for name, e := range crossModMap {
		sc := len(e.Imports) + len(e.ImportedBy) + len(e.Calls) + len(e.CalledBy) + len(e.Inherits) + len(e.InheritedBy)
		scored = append(scored, scoredMod{name: name, entry: e, score: sc})
	}
	sort.Slice(scored, func(i, j int) bool { return scored[i].score > scored[j].score })
	if len(scored) > 100 {
		scored = scored[:100]
	}
	crossModSummary := make(map[string]map[string]any, len(scored))
	for _, sm := range scored {
		e := sm.entry
		crossModSummary[sm.name] = map[string]any{
			"imports":     e.Imports,
			"imported_by": e.ImportedBy,
			"calls":       e.Calls,
			"called_by":   e.CalledBy,
			"inherits":    e.Inherits,
			"inherited_by": e.InheritedBy,
		}
	}

	// File list (sorted)
	files := make([]string, len(result.FilesSeen))
	copy(files, result.FilesSeen)
	sort.Strings(files)

	// Diagrams
	diagramData := make(map[string]string)
	for name, d := range diagrams {
		diagramData[name] = fmt.Sprintf("```mermaid\n%s\n```", d[1])
	}

	return map[string]any{
		"files_seen":          files,
		"entry_points":        result.EntryPoints,
		"symbols":             topSymbols,
		"symbol_table":        symbolTable,
		"relationships":       relSummary,
		"relationship_stats":  relationshipStats,
		"cross_module_summary": crossModSummary,
		"build_commands":      result.BuildCommands,
		"test_commands":       result.TestCommands,
		"risks":               result.Risks,
		"evidence":            result.Evidence,
		"diagrams":            diagramData,
		"symbol_count":        len(result.Symbols),
		"file_count":          len(result.FilesSeen),
		"relationship_count":  len(result.Relationships),
	}
}

// slicePayload returns only the keys listed in requiredData (plus always-included keys).
// If requiredData is empty, returns the full payload.
func slicePayload(full map[string]any, requiredData []string) map[string]any {
	alwaysInclude := map[string]bool{
		"file_count": true, "symbol_count": true,
		"relationship_count": true, "entry_points": true,
		"build_commands": true, "test_commands": true,
	}

	if len(requiredData) == 0 {
		return full
	}

	sliced := make(map[string]any)
	for _, key := range requiredData {
		if v, ok := full[key]; ok {
			sliced[key] = v
		}
	}
	for key := range alwaysInclude {
		if v, ok := full[key]; ok {
			sliced[key] = v
		}
	}
	return sliced
}

const rekipediaVersion = "0.9.16"

// ensureFrontmatter prepends YAML frontmatter to content if not already present.
func ensureFrontmatter(spec models.WikiPageSpec, content string) string {
	if strings.HasPrefix(content, "---") {
		return content
	}
	importance := spec.Importance
	if importance == 0 {
		importance = 50
	}
	section := spec.Section
	if section == "" {
		section = "general"
	}
	createdAt := time.Now().UTC().Format("2006-01-02T15:04:05Z")
	fm := fmt.Sprintf("---\nslug: %s\ntitle: %q\ncreated_at: %s\nrekipedia_version: %s\nimportance: %d\nsection: %s\npin: false\n---\n\n",
		spec.Slug, spec.Title, createdAt, rekipediaVersion, importance, section)
	return fm + content
}
