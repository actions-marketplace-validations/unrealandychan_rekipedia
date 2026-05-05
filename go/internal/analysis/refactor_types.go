// Package analysis — shared types for refactoring analysis.
//
// This file is the single source of truth for data types shared across
// refactor_detector.go, refactor_enricher.go, and refactor_writer.go.
// Do NOT redeclare these types in any other file in this package.
package analysis

// ── Severity constants ────────────────────────────────────────────────────────

const (
	SeverityHigh   = "high"
	SeverityMedium = "medium"
	SeverityLow    = "low"
)

// ── Core data model ───────────────────────────────────────────────────────────

// RefactorIssue represents a single detected refactoring opportunity.
// Metrics is a flexible map so that detectors with different metric sets
// (fan_in, fan_out, lines, depth, cycle_members …) can all use the same type.
//
// LLM enrichment fields (Problem, Suggestion, StartHere, Risk) are populated
// by RefactorEnricher.Enrich(); they are empty strings when --no-llm is set.
type RefactorIssue struct {
	Kind     string         `json:"kind"`     // "god_class" | "circular_dep" | "dead_code" | "large_file" | "high_coupling" | "high_fan_in" | "high_fan_out" | "deep_inheritance"
	Symbol   string         `json:"symbol"`   // primary symbol / file name
	File     string         `json:"file"`     // source file path
	Severity string         `json:"severity"` // "high" | "medium" | "low"
	Metrics  map[string]any `json:"metrics"`  // raw numeric metrics (keys vary by kind)
	Callers  []string       `json:"callers"`  // top callers / dependents
	Notes    []string       `json:"notes"`    // relevant tech-lead notes (from wiki)

	// Populated by LLM enrichment (empty when --no-llm)
	Problem    string `json:"problem,omitempty"`
	Suggestion string `json:"suggestion,omitempty"`
	StartHere  string `json:"start_here,omitempty"`
	Risk       string `json:"risk,omitempty"`
}

// RefactorSummary counts issues by severity.
type RefactorSummary struct {
	High   int `json:"high"`
	Medium int `json:"medium"`
	Low    int `json:"low"`
}

// ── Shared detection helpers ──────────────────────────────────────────────────

// godClassDegreeThreshold is the minimum combined fan-in + fan-out for a
// symbol to be flagged as a God Class.
const godClassDegreeThreshold = 10

// testPrefixes lists name prefixes that identify test helpers.
var testPrefixes = []string{"test_", "Test", "spec_", "Spec"}

// testPathSubstrings lists path fragments that identify test files.
var testPathSubstrings = []string{"/test", "\\test", "_test", "test_", "spec_", "_spec"}

// RefactorReport is the machine-readable JSON output written to refactor_report.json.
type RefactorReport struct {
	GeneratedAt      string          `json:"generated_at"`
	RekipediaVersion string          `json:"rekipedia_version"`
	Summary          RefactorSummary `json:"summary"`
	Issues           []RefactorIssue `json:"issues"`
}
