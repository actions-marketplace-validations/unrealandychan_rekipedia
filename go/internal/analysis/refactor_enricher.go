// Package analysis provides static-analysis and LLM-enrichment utilities
// for refactoring issue detection.
//
// Mirrors src/rekipedia/analysis/refactor_enricher.py.
package analysis

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"

	"github.com/unrealandychan/rekipedia/internal/llm"
	"github.com/unrealandychan/rekipedia/internal/models"
)

// ── Thresholds ────────────────────────────────────────────────────────────────
// godClassDegreeThreshold is defined in refactor_types.go.

const (
	largeFileSymbolThreshold = 30
	highCouplingOutThreshold = 10
	deadCodeMinFileSymbols   = 3
	maxEnricherWorkers       = 4
	maxCycles                = 20
	maxCycleLen              = 8
)

// ── Data model ────────────────────────────────────────────────────────────────

// RefactorIssue is defined in refactor_types.go.

// ── Prompt templates ──────────────────────────────────────────────────────────

const systemPrompt = `You are a senior software architect reviewing code for refactoring opportunities.
Given a code issue detected by static analysis, produce a concise, actionable
refactoring recommendation.

Respond in EXACTLY this format — no extra text, no markdown headers:
Problem: <one sentence describing the concrete issue>
Suggestion: <specific refactoring action — name the new components/functions>
Start here: <file or component — the safest/lowest-coupling place to begin>
Risk: <Low|Medium|High> — <one sentence explaining the primary risk>`

var issuePrompts = map[string]string{
	"god_class": `Symbol: %s
File: %s
Issue type: God class / hub node
Degree: %d (%d callers, %d outbound dependencies)
Top callers: %s
Relevant notes: %s

This symbol has extremely high coupling, suggesting it handles too many responsibilities.
Suggest how to split it into focused, single-responsibility components.`,

	"circular_dep": `Cycle members: %s
Files involved: %s
Issue type: Circular dependency
Cycle length: %d
Relevant notes: %s

This circular dependency creates tight coupling and makes the code hard to test or deploy.
Suggest how to break the cycle using dependency inversion or an intermediary module.`,

	"dead_code": `Symbol: %s
File: %s
Issue type: Dead code — no callers detected
Total symbols in file: %d
Relevant notes: %s

This exported symbol appears to be unused by any other module.
Suggest whether to remove it, deprecate it, or repurpose it.`,

	"large_file": `File: %s
Issue type: Large file — too many symbols
Symbol count: %d
Top symbols: %s
Relevant notes: %s

This file defines too many symbols and likely handles multiple concerns.
Suggest how to split it into focused, cohesive modules.`,

	"high_coupling": `Symbol: %s
File: %s
Issue type: High coupling — too many outbound dependencies
Outbound dependencies: %d
Top dependencies: %s
Relevant notes: %s

This symbol imports from / calls too many distinct modules.
Suggest dependency-reduction strategies (facade, adapter, or domain split).`,
}

// ── Static analysis ───────────────────────────────────────────────────────────

// DetectIssues runs static analysis on result and returns a list of RefactorIssues.
// No LLM calls are made. Mirrors Python detect_issues().
func DetectIssues(result models.AnalysisResult) []RefactorIssue {
	var issues []RefactorIssue
	seen := make(map[string]bool) // "kind|symbol"

	add := func(issue RefactorIssue) {
		key := issue.Kind + "|" + issue.Symbol
		if !seen[key] {
			seen[key] = true
			issues = append(issues, issue)
		}
	}

	// ── Build degree maps ──────────────────────────────────────────
	inDeg := make(map[string]int)
	outDeg := make(map[string]int)
	callInDeg := make(map[string]int)
	adj := make(map[string]map[string]bool)

	for _, rel := range result.Relationships {
		if rel.From == "" || rel.To == "" {
			continue
		}
		outDeg[rel.From]++
		inDeg[rel.To]++
		k := string(rel.Kind)
		if k == "call" || k == "calls" {
			callInDeg[rel.To]++
		}
		if k == "import" || k == "imports" || k == "call" || k == "calls" || k == "uses" {
			if adj[rel.From] == nil {
				adj[rel.From] = make(map[string]bool)
			}
			adj[rel.From][rel.To] = true
		}
	}

	// ── Symbol maps ────────────────────────────────────────────────
	symFile := make(map[string]string)
	symKind := make(map[string]string)
	symbolsPerFile := make(map[string][]string)

	for _, sym := range result.Symbols {
		symFile[sym.Name] = sym.File
		symKind[sym.Name] = string(sym.Kind)
		if sym.File != "" {
			symbolsPerFile[sym.File] = append(symbolsPerFile[sym.File], sym.Name)
		}
	}

	// ── God class ──────────────────────────────────────────────────
	allNodes := make(map[string]bool)
	for k := range inDeg {
		allNodes[k] = true
	}
	for k := range outDeg {
		allNodes[k] = true
	}
	for name := range allNodes {
		total := inDeg[name] + outDeg[name]
		if total >= godClassDegreeThreshold {
			add(RefactorIssue{
				Kind:   "god_class",
				Symbol: name,
				File:   symFile[name],
				Metrics: map[string]any{
					"degree":     total,
					"in_degree":  inDeg[name],
					"out_degree": outDeg[name],
				},
			})
		}
	}

	// ── High coupling ──────────────────────────────────────────────
	for name, od := range outDeg {
		if od >= highCouplingOutThreshold {
			add(RefactorIssue{
				Kind:   "high_coupling",
				Symbol: name,
				File:   symFile[name],
				Metrics: map[string]any{
					"out_degree": od,
				},
			})
		}
	}

	// ── Circular dependencies ──────────────────────────────────────
	for _, cycle := range findCycles(adj) {
		members := sortedSlice(cycle)
		files := uniqueFiles(members, symFile)
		add(RefactorIssue{
			Kind:   "circular_dep",
			Symbol: strings.Join(members, ", "),
			File:   strings.Join(files, ", "),
			Metrics: map[string]any{
				"cycle_length": len(cycle),
				"members":      members,
			},
		})
	}

	// ── Dead code ──────────────────────────────────────────────────
	validKinds := map[string]bool{"function": true, "method": true, "class": true}
	for _, sym := range result.Symbols {
		if !validKinds[string(sym.Kind)] {
			continue
		}
		if callInDeg[sym.Name] > 0 {
			continue
		}
		if len(symbolsPerFile[sym.File]) < deadCodeMinFileSymbols {
			continue
		}
		if strings.HasPrefix(sym.Name, "test_") ||
			strings.Contains(sym.File, "test") {
			continue
		}
		add(RefactorIssue{
			Kind:   "dead_code",
			Symbol: sym.Name,
			File:   sym.File,
			Metrics: map[string]any{
				"total_symbols": len(symbolsPerFile[sym.File]),
			},
		})
	}

	// ── Large file ─────────────────────────────────────────────────
	for fpath, syms := range symbolsPerFile {
		if len(syms) >= largeFileSymbolThreshold {
			top := syms
			if len(top) > 10 {
				top = top[:10]
			}
			add(RefactorIssue{
				Kind:   "large_file",
				Symbol: strings.Join(top, ", "),
				File:   fpath,
				Metrics: map[string]any{
					"symbol_count": len(syms),
				},
			})
		}
	}

	return issues
}

// AttachCallers populates the Callers field of each issue (top-5 call-graph callers).
func AttachCallers(issues []RefactorIssue, result models.AnalysisResult, topN int) {
	callersOf := make(map[string][]string)
	for _, rel := range result.Relationships {
		k := string(rel.Kind)
		if (k == "call" || k == "calls") && rel.From != "" && rel.To != "" {
			callersOf[rel.To] = append(callersOf[rel.To], rel.From)
		}
	}
	for i := range issues {
		callers := dedup(callersOf[issues[i].Symbol])
		if len(callers) > topN {
			callers = callers[:topN]
		}
		issues[i].Callers = callers
	}
}

// AttachNotes populates the Notes field of each issue from tech-lead notes.
// notes is a list of maps with keys "file", "tag", "content".
func AttachNotes(issues []RefactorIssue, notes []map[string]string) {
	notesByFile := make(map[string][]string)
	for _, n := range notes {
		f := n["file"]
		content := n["content"]
		if f != "" && content != "" {
			text := fmt.Sprintf("[%s] %s", n["tag"], content)
			notesByFile[f] = append(notesByFile[f], text)
		}
	}
	for i := range issues {
		var matched []string
		for fpath, texts := range notesByFile {
			if strings.Contains(issues[i].File, fpath) || strings.Contains(fpath, issues[i].File) {
				matched = append(matched, texts...)
			}
		}
		if len(matched) > 5 {
			matched = matched[:5]
		}
		issues[i].Notes = matched
	}
}

// ── LLM enricher ─────────────────────────────────────────────────────────────

// RefactorEnricher enriches static-analysis issues with LLM explanations.
// Pass a nil Caller to skip LLM calls (--no-llm mode).
type RefactorEnricher struct {
	client llm.Caller // nil → skip enrichment
}

// NewRefactorEnricher creates an enricher backed by the given LLM client.
// Pass nil to operate in static-analysis-only mode.
func NewRefactorEnricher(client llm.Caller) *RefactorEnricher {
	return &RefactorEnricher{client: client}
}

// EnrichAll detects issues from result, attaches callers and notes, and
// enriches them with LLM explanations (concurrently). Returns the enriched list.
func (e *RefactorEnricher) EnrichAll(
	ctx context.Context,
	result models.AnalysisResult,
	notes []map[string]string,
) []RefactorIssue {
	issues := DetectIssues(result)
	AttachCallers(issues, result, 5)
	if len(notes) > 0 {
		AttachNotes(issues, notes)
	}
	return e.Enrich(ctx, issues)
}

// Enrich enriches a pre-built list of issues concurrently. Issues are mutated
// in-place. Returns the same slice for convenience.
// If no LLM client was provided the issues are returned unchanged.
func (e *RefactorEnricher) Enrich(ctx context.Context, issues []RefactorIssue) []RefactorIssue {
	if e.client == nil || len(issues) == 0 {
		return issues
	}

	sem := make(chan struct{}, maxEnricherWorkers)
	var wg sync.WaitGroup

	for i := range issues {
		i := i
		wg.Add(1)
		sem <- struct{}{}
		go func() {
			defer wg.Done()
			defer func() { <-sem }()
			if err := e.enrichOne(ctx, &issues[i]); err != nil {
				// Log but don't fail the whole batch
				_ = err
			}
		}()
	}
	wg.Wait()
	return issues
}

func (e *RefactorEnricher) enrichOne(ctx context.Context, issue *RefactorIssue) error {
	prompt := buildPrompt(issue)
	raw, err := e.client.Call(ctx, systemPrompt, prompt)
	if err != nil {
		return fmt.Errorf("enrich %s/%s: %w", issue.Kind, issue.Symbol, err)
	}
	parseEnrichment(raw, issue)
	return nil
}

// ── Prompt helpers ────────────────────────────────────────────────────────────

func buildPrompt(issue *RefactorIssue) string {
	callers := "(none detected)"
	if len(issue.Callers) > 0 {
		callers = strings.Join(issue.Callers, ", ")
	}
	notes := "(none)"
	if len(issue.Notes) > 0 {
		notes = strings.Join(issue.Notes, "; ")
	}
	file := issue.File
	if file == "" {
		file = "(unknown)"
	}

	switch issue.Kind {
	case "god_class":
		deg := intMetric(issue.Metrics, "degree")
		inD := intMetric(issue.Metrics, "in_degree")
		outD := intMetric(issue.Metrics, "out_degree")
		return fmt.Sprintf(issuePrompts["god_class"],
			issue.Symbol, file, deg, inD, outD, callers, notes)
	case "circular_dep":
		cl := intMetric(issue.Metrics, "cycle_length")
		return fmt.Sprintf(issuePrompts["circular_dep"],
			issue.Symbol, file, cl, notes)
	case "dead_code":
		ts := intMetric(issue.Metrics, "total_symbols")
		return fmt.Sprintf(issuePrompts["dead_code"],
			issue.Symbol, file, ts, notes)
	case "large_file":
		sc := intMetric(issue.Metrics, "symbol_count")
		return fmt.Sprintf(issuePrompts["large_file"],
			file, sc, issue.Symbol, notes)
	case "high_coupling":
		outD := intMetric(issue.Metrics, "out_degree")
		return fmt.Sprintf(issuePrompts["high_coupling"],
			issue.Symbol, file, outD, callers, notes)
	default:
		deg := intMetric(issue.Metrics, "degree")
		inD := intMetric(issue.Metrics, "in_degree")
		outD := intMetric(issue.Metrics, "out_degree")
		return fmt.Sprintf(issuePrompts["god_class"],
			issue.Symbol, file, deg, inD, outD, callers, notes)
	}
}

func parseEnrichment(raw string, issue *RefactorIssue) {
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		lower := strings.ToLower(line)
		switch {
		case strings.HasPrefix(lower, "problem:"):
			issue.Problem = strings.TrimSpace(line[len("problem:"):])
		case strings.HasPrefix(lower, "suggestion:"):
			issue.Suggestion = strings.TrimSpace(line[len("suggestion:"):])
		case strings.HasPrefix(lower, "start here:"):
			issue.StartHere = strings.TrimSpace(line[len("start here:"):])
		case strings.HasPrefix(lower, "risk:"):
			issue.Risk = strings.TrimSpace(line[len("risk:"):])
		}
	}
}

// ── Graph helpers ─────────────────────────────────────────────────────────────

// findCycles returns small cycles (≤ maxCycleLen nodes) via iterative DFS.
// Capped at maxCycles to avoid flooding output.
func findCycles(adj map[string]map[string]bool) [][]string {
	var found [][]string
	seenSets := make(map[string]bool)

	type frame struct {
		node string
		path []string
	}

	for start := range adj {
		if len(found) >= maxCycles {
			break
		}
		stack := []frame{{start, []string{start}}}
		for len(stack) > 0 && len(found) < maxCycles {
			f := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			for nb := range adj[f.node] {
				if nb == f.path[0] {
					key := cycleKey(f.path)
					if !seenSets[key] && len(f.path) >= 2 {
						seenSets[key] = true
						cp := make([]string, len(f.path))
						copy(cp, f.path)
						found = append(found, cp)
					}
				} else if !inSlice(f.path, nb) && len(f.path) < maxCycleLen {
					newPath := make([]string, len(f.path)+1)
					copy(newPath, f.path)
					newPath[len(f.path)] = nb
					stack = append(stack, frame{nb, newPath})
				}
			}
		}
	}
	return found
}

func cycleKey(path []string) string {
	cp := make([]string, len(path))
	copy(cp, path)
	sort.Strings(cp)
	return strings.Join(cp, "|")
}

func inSlice(s []string, v string) bool {
	for _, x := range s {
		if x == v {
			return true
		}
	}
	return false
}

func sortedSlice(members []string) []string {
	cp := make([]string, len(members))
	copy(cp, members)
	sort.Strings(cp)
	return cp
}

func uniqueFiles(members []string, symFile map[string]string) []string {
	seen := make(map[string]bool)
	var result []string
	for _, m := range members {
		f := symFile[m]
		if f == "" {
			f = m
		}
		if !seen[f] {
			seen[f] = true
			result = append(result, f)
		}
	}
	sort.Strings(result)
	return result
}

func dedup(s []string) []string {
	seen := make(map[string]bool)
	var result []string
	for _, v := range s {
		if !seen[v] {
			seen[v] = true
			result = append(result, v)
		}
	}
	return result
}

func intMetric(m map[string]any, key string) int {
	if m == nil {
		return 0
	}
	v, ok := m[key]
	if !ok {
		return 0
	}
	switch x := v.(type) {
	case int:
		return x
	case float64:
		return int(x)
	}
	return 0
}
