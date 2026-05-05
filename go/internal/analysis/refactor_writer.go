// Package analysis provides static-analysis utilities including refactoring
// issue detection and report generation.
package analysis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/unrealandychan/rekipedia/internal/models"
)

// ── Severity constants ────────────────────────────────────────────────────────

const (
	SeverityHigh   = "high"
	SeverityMedium = "medium"
	SeverityLow    = "low"
)

var severityEmoji = map[string]string{
	SeverityHigh:   "🔴",
	SeverityMedium: "🟡",
	SeverityLow:    "🟢",
}

var sectionTitle = map[string]string{
	SeverityHigh:   "High Priority",
	SeverityMedium: "Medium Priority",
	SeverityLow:    "Quick Wins (Dead Code)",
}

// godClassDegreeThreshold is the minimum combined fan-in + fan-out for a
// symbol to be flagged as a God Class.
const godClassDegreeThreshold = 10

// testPrefixes lists name prefixes that identify test helpers.
var testPrefixes = []string{"test_", "Test", "spec_", "Spec"}

// testPathSubstrings lists path fragments that identify test files.
var testPathSubstrings = []string{"/test", "\\test", "_test", "test_", "spec_", "_spec"}

// ── Data structures ───────────────────────────────────────────────────────────

// RefactorMetrics holds quantitative measurements for a detected issue.
type RefactorMetrics struct {
	Lines  int `json:"lines,omitempty"`
	FanIn  int `json:"fan_in"`
	FanOut int `json:"fan_out"`
}

// RefactorIssue represents a single detected refactoring opportunity.
type RefactorIssue struct {
	Kind       string          `json:"kind"`
	Symbol     string          `json:"symbol"`
	File       string          `json:"file"`
	Severity   string          `json:"severity"`
	Metrics    RefactorMetrics `json:"metrics"`
	Suggestion string          `json:"suggestion"`
	Callers    []string        `json:"callers"`
}

// RefactorSummary counts issues by severity.
type RefactorSummary struct {
	High   int `json:"high"`
	Medium int `json:"medium"`
	Low    int `json:"low"`
}

// RefactorReport is the machine-readable JSON output.
type RefactorReport struct {
	GeneratedAt      string          `json:"generated_at"`
	RekipediaVersion string          `json:"rekipedia_version"`
	Summary          RefactorSummary `json:"summary"`
	Issues           []RefactorIssue `json:"issues"`
}

// ── Detection logic ────────────────────────────────────────────────────────────

// DetectIssues analyses an AnalysisResult and returns detected refactoring
// issues sorted by severity (high → medium → low) and then alphabetically.
func DetectIssues(combined models.AnalysisResult) []RefactorIssue {
	var issues []RefactorIssue

	// Build degree maps
	inDeg := make(map[string]int)
	outDeg := make(map[string]int)
	callersMap := make(map[string][]string)

	for _, rel := range combined.Relationships {
		if rel.From != "" {
			outDeg[rel.From]++
		}
		if rel.To != "" {
			inDeg[rel.To]++
		}
		k := strings.ToLower(string(rel.Kind))
		if (k == "call" || k == "calls") && rel.From != "" && rel.To != "" {
			callersMap[rel.To] = append(callersMap[rel.To], rel.From)
		}
	}

	// Build symbol lookup
	symLookup := make(map[string]models.Symbol, len(combined.Symbols))
	for _, sym := range combined.Symbols {
		symLookup[sym.Name] = sym
	}

	// Entry points set
	entrySet := make(map[string]bool, len(combined.EntryPoints))
	for _, ep := range combined.EntryPoints {
		entrySet[ep] = true
	}

	// ── 1. God Class detection ─────────────────────────────────────────────
	for name, sym := range symLookup {
		kind := string(sym.Kind)
		if kind != "class" && kind != "interface" {
			continue
		}

		fanIn := inDeg[name]
		fanOut := outDeg[name]
		degree := fanIn + fanOut

		if degree < godClassDegreeThreshold {
			continue
		}

		lines := 0
		if sym.LineEnd > sym.LineStart {
			lines = sym.LineEnd - sym.LineStart
		}

		callers := uniqueStrings(callersMap[name])
		if len(callers) > 20 {
			callers = callers[:20]
		}

		issues = append(issues, RefactorIssue{
			Kind:     "god_class",
			Symbol:   name,
			File:     sym.File,
			Severity: SeverityHigh,
			Metrics: RefactorMetrics{
				Lines:  lines,
				FanIn:  fanIn,
				FanOut: fanOut,
			},
			Suggestion: fmt.Sprintf("Split `%s` into smaller, single-responsibility classes", name),
			Callers:    callers,
		})
	}

	// ── 2. Dead Code detection ─────────────────────────────────────────────
	for name, sym := range symLookup {
		kind := string(sym.Kind)
		if kind != "function" && kind != "method" {
			continue
		}
		if entrySet[name] {
			continue
		}
		// Skip test helpers
		isTestHelper := false
		for _, pfx := range testPrefixes {
			if strings.HasPrefix(name, pfx) {
				isTestHelper = true
				break
			}
		}
		if isTestHelper {
			continue
		}
		// Skip dunder methods
		if strings.HasPrefix(name, "__") && strings.HasSuffix(name, "__") {
			continue
		}
		// Skip symbols defined in test files
		isTestFile := false
		for _, sub := range testPathSubstrings {
			if strings.Contains(sym.File, sub) {
				isTestFile = true
				break
			}
		}
		if isTestFile {
			continue
		}

		if len(callersMap[name]) > 0 {
			continue
		}

		issues = append(issues, RefactorIssue{
			Kind:     "dead_code",
			Symbol:   name,
			File:     sym.File,
			Severity: SeverityLow,
			Metrics: RefactorMetrics{
				FanIn:  0,
				FanOut: outDeg[name],
			},
			Suggestion: fmt.Sprintf("Remove `%s` — 0 callers detected", name),
			Callers:    []string{},
		})
	}

	// Sort: high → medium → low, then alphabetically
	severityOrder := map[string]int{SeverityHigh: 0, SeverityMedium: 1, SeverityLow: 2}
	sort.Slice(issues, func(i, j int) bool {
		oi := severityOrder[issues[i].Severity]
		oj := severityOrder[issues[j].Severity]
		if oi != oj {
			return oi < oj
		}
		return issues[i].Symbol < issues[j].Symbol
	})

	return issues
}

// ── Markdown rendering ─────────────────────────────────────────────────────────

// BuildMarkdown renders a REFACTOR.md document from the detected issues.
func BuildMarkdown(issues []RefactorIssue, fileCount int, version string) string {
	timestamp := time.Now().UTC().Format("2006-01-02T15:04:05Z")
	n := len(issues)
	issueWord := "issues"
	if n == 1 {
		issueWord = "issue"
	}
	fileWord := "files"
	if fileCount == 1 {
		fileWord = "file"
	}

	var sb strings.Builder
	sb.WriteString("# Refactoring Guide\n")
	sb.WriteString(fmt.Sprintf("> Generated by rekipedia v%s — %s\n", version, timestamp))
	sb.WriteString(fmt.Sprintf("> %d %s found across %d %s\n\n", n, issueWord, fileCount, fileWord))

	// Group by severity preserving order
	bySeverity := map[string][]RefactorIssue{
		SeverityHigh:   {},
		SeverityMedium: {},
		SeverityLow:    {},
	}
	for _, issue := range issues {
		bySeverity[issue.Severity] = append(bySeverity[issue.Severity], issue)
	}

	for _, sev := range []string{SeverityHigh, SeverityMedium, SeverityLow} {
		sevIssues := bySeverity[sev]
		if len(sevIssues) == 0 {
			continue
		}
		emoji := severityEmoji[sev]
		title := sectionTitle[sev]
		sb.WriteString(fmt.Sprintf("## %s %s\n\n", emoji, title))

		if sev == SeverityLow {
			// Dead code — compact bulleted list
			for _, issue := range sevIssues {
				note := strings.Replace(issue.Suggestion,
					fmt.Sprintf("Remove `%s` — ", issue.Symbol), "", 1)
				prefix := ""
				if issue.File != "" {
					prefix = fmt.Sprintf("`%s:`", issue.File)
				}
				sb.WriteString(fmt.Sprintf("- %s`%s()` — %s\n", prefix, issue.Symbol, note))
			}
			sb.WriteString("\n")
		} else {
			for i, issue := range sevIssues {
				words := strings.Fields(strings.ReplaceAll(issue.Kind, "_", " "))
				for wi, w := range words {
					if len(w) > 0 {
						words[wi] = strings.ToUpper(w[:1]) + w[1:]
					}
				}
				kindLabel := strings.Join(words, " ")

				sb.WriteString(fmt.Sprintf("### %d. Split `%s` (%s)\n", i+1, issue.Symbol, kindLabel))

				var problemParts []string
				if issue.Metrics.Lines > 0 {
					problemParts = append(problemParts, fmt.Sprintf("%d lines", issue.Metrics.Lines))
				}
				if issue.Metrics.FanIn > 0 || issue.Metrics.FanOut > 0 {
					problemParts = append(problemParts,
						fmt.Sprintf("fan_in=%d, fan_out=%d", issue.Metrics.FanIn, issue.Metrics.FanOut))
				}
				problemStr := "high coupling"
				if len(problemParts) > 0 {
					problemStr = strings.Join(problemParts, ", ")
				}
				sb.WriteString(fmt.Sprintf("- **Problem**: %s\n", problemStr))
				sb.WriteString(fmt.Sprintf("- **Suggestion**: %s\n", issue.Suggestion))
				sb.WriteString(fmt.Sprintf("- **Callers affected**: %d\n", issue.Metrics.FanIn))
				if issue.File != "" {
					sb.WriteString(fmt.Sprintf("- **File**: `%s`\n", issue.File))
				}
				sb.WriteString("\n")
			}
		}
	}

	return sb.String()
}

// ── File output ────────────────────────────────────────────────────────────────

// WriteRefactorOutputs writes REFACTOR.md and refactor_report.json to outputDir.
// When stdout is true, REFACTOR.md content is also written to os.Stdout.
func WriteRefactorOutputs(combined models.AnalysisResult, outputDir string, version string, stdout bool) error {
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", outputDir, err)
	}

	issues := DetectIssues(combined)
	fileCount := len(combined.FilesSeen)

	// ── Markdown ──────────────────────────────────────────────────────────
	mdContent := BuildMarkdown(issues, fileCount, version)
	mdPath := filepath.Join(outputDir, "REFACTOR.md")
	if err := os.WriteFile(mdPath, []byte(mdContent), 0o644); err != nil {
		return fmt.Errorf("write REFACTOR.md: %w", err)
	}

	if stdout {
		if _, err := fmt.Fprint(os.Stdout, mdContent); err != nil {
			return fmt.Errorf("write REFACTOR.md to stdout: %w", err)
		}
	}

	// ── JSON ──────────────────────────────────────────────────────────────
	var summary RefactorSummary
	for _, issue := range issues {
		switch issue.Severity {
		case SeverityHigh:
			summary.High++
		case SeverityMedium:
			summary.Medium++
		case SeverityLow:
			summary.Low++
		}
	}

	// Ensure Issues is never null in JSON
	if issues == nil {
		issues = []RefactorIssue{}
	}

	report := RefactorReport{
		GeneratedAt:      time.Now().UTC().Format(time.RFC3339),
		RekipediaVersion: version,
		Summary:          summary,
		Issues:           issues,
	}

	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal refactor report: %w", err)
	}

	jsonPath := filepath.Join(outputDir, "refactor_report.json")
	if err := os.WriteFile(jsonPath, data, 0o644); err != nil {
		return fmt.Errorf("write refactor_report.json: %w", err)
	}

	return nil
}

// ── Helpers ────────────────────────────────────────────────────────────────────

// uniqueStrings returns a deduplicated copy of ss preserving first-seen order.
func uniqueStrings(ss []string) []string {
	seen := make(map[string]bool, len(ss))
	out := make([]string, 0, len(ss))
	for _, s := range ss {
		if !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	return out
}
