package analysis

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/unrealandychan/rekipedia/internal/models"
)

// ── helpers ───────────────────────────────────────────────────────────────────

func wRel(from, to, kind string) models.Relationship {
	return models.Relationship{From: from, To: to, Kind: models.RelKind(kind)}
}

func wSym(name, kind, file string) models.Symbol {
	return models.Symbol{Name: name, Kind: models.SymbolKind(kind), File: file}
}

func wMakeResult(syms []models.Symbol, rels []models.Relationship, eps []string) models.AnalysisResult {
	return models.AnalysisResult{
		ShardID:       "test",
		FilesSeen:     []string{"src/app.go"},
		EntryPoints:   eps,
		Symbols:       syms,
		Relationships: rels,
		Evidence:      map[string]string{},
	}
}

// ── DetectIssues: god class ────────────────────────────────────────────────────

func TestDetectGodClassAboveThreshold(t *testing.T) {
	// 6 callers + 5 callees = 11 degrees → god class
	syms := []models.Symbol{wSym("BigClass", "class", "src/big.go")}
	var rels []models.Relationship
	for i := 0; i < 6; i++ {
		rels = append(rels, wRel(strings.Repeat("c", i+1), "BigClass", "calls"))
	}
	for i := 0; i < 5; i++ {
		rels = append(rels, wRel("BigClass", strings.Repeat("d", i+1), "calls"))
	}
	combined := wMakeResult(syms, rels, nil)
	issues := DetectWriterIssues(combined)

	godIssues := filterKind(issues, "god_class")
	if len(godIssues) == 0 {
		t.Fatal("expected at least one god_class issue")
	}
	if godIssues[0].Symbol != "BigClass" {
		t.Errorf("expected BigClass, got %s", godIssues[0].Symbol)
	}
	if godIssues[0].Severity != SeverityHigh {
		t.Errorf("expected high severity, got %s", godIssues[0].Severity)
	}
	if intMetric(godIssues[0].Metrics, "fan_in") != 6 {
		t.Errorf("expected fan_in=6, got %d", intMetric(godIssues[0].Metrics, "fan_in"))
	}
	if intMetric(godIssues[0].Metrics, "fan_out") != 5 {
		t.Errorf("expected fan_out=5, got %d", intMetric(godIssues[0].Metrics, "fan_out"))
	}
}

func TestDetectGodClassBelowThreshold(t *testing.T) {
	syms := []models.Symbol{wSym("SmallClass", "class", "src/small.go")}
	rels := []models.Relationship{
		wRel("A", "SmallClass", "calls"),
		wRel("SmallClass", "B", "calls"),
		wRel("SmallClass", "C", "calls"),
	}
	combined := wMakeResult(syms, rels, nil)
	issues := DetectWriterIssues(combined)

	godIssues := filterKind(issues, "god_class")
	if len(godIssues) != 0 {
		t.Errorf("expected no god_class issues, got %d", len(godIssues))
	}
}

func TestDetectGodClassCallersCapped(t *testing.T) {
	syms := []models.Symbol{wSym("HugeClass", "class", "src/huge.go")}
	var rels []models.Relationship
	for i := 0; i < 30; i++ {
		rels = append(rels, wRel(strings.Repeat("x", i+1), "HugeClass", "calls"))
	}
	combined := wMakeResult(syms, rels, nil)
	issues := DetectWriterIssues(combined)

	godIssues := filterKind(issues, "god_class")
	if len(godIssues) == 0 {
		t.Fatal("expected a god_class issue")
	}
	if len(godIssues[0].Callers) > 20 {
		t.Errorf("callers should be capped at 20, got %d", len(godIssues[0].Callers))
	}
}

// ── DetectIssues: dead code ────────────────────────────────────────────────────

func TestDetectDeadCodeZeroCallers(t *testing.T) {
	syms := []models.Symbol{wSym("orphaned_func", "function", "src/app.go")}
	combined := wMakeResult(syms, nil, nil)
	issues := DetectWriterIssues(combined)

	dead := filterKind(issues, "dead_code")
	found := false
	for _, i := range dead {
		if i.Symbol == "orphaned_func" {
			found = true
		}
	}
	if !found {
		t.Error("expected orphaned_func to be flagged as dead code")
	}
}

func TestDetectDeadCodeWithCallerExcluded(t *testing.T) {
	syms := []models.Symbol{wSym("live_func", "function", "src/app.go")}
	rels := []models.Relationship{wRel("some_caller", "live_func", "calls")}
	combined := wMakeResult(syms, rels, nil)
	issues := DetectWriterIssues(combined)

	for _, i := range issues {
		if i.Symbol == "live_func" {
			t.Error("live_func should not be flagged as dead code")
		}
	}
}

func TestDetectDeadCodeSkipsEntryPoints(t *testing.T) {
	syms := []models.Symbol{wSym("main_func", "function", "src/main.go")}
	combined := wMakeResult(syms, nil, []string{"main_func"})
	issues := DetectWriterIssues(combined)

	for _, i := range issues {
		if i.Symbol == "main_func" {
			t.Error("entry point should not be flagged as dead code")
		}
	}
}

func TestDetectDeadCodeSkipsDunder(t *testing.T) {
	syms := []models.Symbol{wSym("__init__", "function", "src/app.py")}
	combined := wMakeResult(syms, nil, nil)
	issues := DetectWriterIssues(combined)

	for _, i := range issues {
		if i.Symbol == "__init__" {
			t.Error("dunder method should not be flagged as dead code")
		}
	}
}

func TestDetectDeadCodeSkipsTestHelpers(t *testing.T) {
	syms := []models.Symbol{
		wSym("test_something", "function", "src/app.go"),
		wSym("TestSomething", "function", "src/app_test.go"),
	}
	combined := wMakeResult(syms, nil, nil)
	issues := DetectWriterIssues(combined)

	for _, i := range issues {
		if i.Symbol == "test_something" || i.Symbol == "TestSomething" {
			t.Errorf("test helper %q should not be flagged as dead code", i.Symbol)
		}
	}
}

func TestDetectDeadCodeSkipsTestFileSymbols(t *testing.T) {
	syms := []models.Symbol{wSym("helper", "function", "tests/test_util.go")}
	combined := wMakeResult(syms, nil, nil)
	issues := DetectWriterIssues(combined)

	for _, i := range issues {
		if i.Symbol == "helper" {
			t.Error("symbol in test file should not be flagged as dead code")
		}
	}
}

// ── DetectIssues: severity ordering ───────────────────────────────────────────

func TestIssuesSortedHighBeforeLow(t *testing.T) {
	godSym := wSym("GodClass", "class", "src/god.go")
	deadSym := wSym("dead_fn", "function", "src/util.go")
	var rels []models.Relationship
	for i := 0; i < 6; i++ {
		rels = append(rels, wRel(strings.Repeat("c", i+1), "GodClass", "calls"))
	}
	for i := 0; i < 5; i++ {
		rels = append(rels, wRel("GodClass", strings.Repeat("d", i+1), "calls"))
	}
	combined := wMakeResult([]models.Symbol{godSym, deadSym}, rels, nil)
	issues := DetectWriterIssues(combined)

	seenLow := false
	for _, i := range issues {
		if i.Severity == "low" {
			seenLow = true
		}
		if seenLow && i.Severity == "high" {
			t.Error("high severity appeared after low severity")
		}
	}
}

// ── BuildMarkdown ──────────────────────────────────────────────────────────────

func TestBuildMarkdownHeader(t *testing.T) {
	md := BuildMarkdown(nil, 42, "0.9.0")
	if !strings.Contains(md, "# Refactoring Guide") {
		t.Error("missing heading")
	}
	if !strings.Contains(md, "0 issues") {
		t.Error("missing issue count")
	}
	if !strings.Contains(md, "42 files") {
		t.Error("missing file count")
	}
}

func TestBuildMarkdownHighSection(t *testing.T) {
	issue := RefactorIssue{
		Kind: "god_class", Symbol: "BigClass", File: "src/big.go",
		Severity: SeverityHigh,
		Metrics:  map[string]any{"lines": 300, "fan_in": 10, "fan_out": 5},
		Suggestion: "Split BigClass",
		Callers:    []string{"a", "b"},
	}
	md := BuildMarkdown([]RefactorIssue{issue}, 5, "0.9.0")
	if !strings.Contains(md, "🔴") {
		t.Error("missing high-priority emoji")
	}
	if !strings.Contains(md, "High Priority") {
		t.Error("missing section title")
	}
	if !strings.Contains(md, "BigClass") {
		t.Error("missing symbol name")
	}
	if !strings.Contains(md, "300 lines") {
		t.Error("missing lines metric")
	}
}

func TestBuildMarkdownLowSection(t *testing.T) {
	issue := RefactorIssue{
		Kind: "dead_code", Symbol: "old_fn", File: "src/utils.go",
		Severity:   SeverityLow,
		Metrics:    map[string]any{"fan_in": 0, "fan_out": 0},
		Suggestion: "Remove `old_fn` — 0 callers detected",
		Callers:    []string{},
	}
	md := BuildMarkdown([]RefactorIssue{issue}, 3, "0.9.0")
	if !strings.Contains(md, "🟢") {
		t.Error("missing low-priority emoji")
	}
	if !strings.Contains(md, "Quick Wins") {
		t.Error("missing section title")
	}
	if !strings.Contains(md, "old_fn") {
		t.Error("missing symbol name")
	}
}

func TestBuildMarkdownNoEmptySections(t *testing.T) {
	issue := RefactorIssue{
		Kind: "dead_code", Symbol: "stale_fn", File: "src/old.go",
		Severity:   SeverityLow,
		Metrics:    map[string]any{},
		Suggestion: "Remove `stale_fn` — 0 callers detected",
		Callers:    []string{},
	}
	md := BuildMarkdown([]RefactorIssue{issue}, 1, "0.9.0")
	if strings.Contains(md, "🔴") {
		t.Error("high-priority section should not appear when there are no high issues")
	}
	if strings.Contains(md, "🟡") {
		t.Error("medium-priority section should not appear when there are no medium issues")
	}
}

// ── WriteRefactorOutputs ──────────────────────────────────────────────────────

func TestWriteRefactorOutputsCreatesFiles(t *testing.T) {
	dir := t.TempDir()
	combined := wMakeResult(nil, nil, nil)
	combined.FilesSeen = []string{"a.go", "b.go"}

	if err := WriteRefactorOutputs(combined, dir, "0.9.0", false); err != nil {
		t.Fatalf("WriteRefactorOutputs: %v", err)
	}

	mdPath := filepath.Join(dir, "REFACTOR.md")
	if _, err := os.Stat(mdPath); err != nil {
		t.Errorf("REFACTOR.md not created: %v", err)
	}
	jsonPath := filepath.Join(dir, "refactor_report.json")
	if _, err := os.Stat(jsonPath); err != nil {
		t.Errorf("refactor_report.json not created: %v", err)
	}
}

func TestWriteRefactorOutputsJSONStructure(t *testing.T) {
	dir := t.TempDir()
	syms := []models.Symbol{wSym("GodClass", "class", "src/x.go")}
	var rels []models.Relationship
	for i := 0; i < 6; i++ {
		rels = append(rels, wRel(strings.Repeat("c", i+1), "GodClass", "calls"))
	}
	for i := 0; i < 5; i++ {
		rels = append(rels, wRel("GodClass", strings.Repeat("d", i+1), "calls"))
	}
	combined := wMakeResult(syms, rels, nil)
	combined.FilesSeen = []string{"src/x.go"}

	if err := WriteRefactorOutputs(combined, dir, "0.9.0", false); err != nil {
		t.Fatalf("WriteRefactorOutputs: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(dir, "refactor_report.json"))
	if err != nil {
		t.Fatalf("read json: %v", err)
	}
	var report RefactorReport
	if err := json.Unmarshal(data, &report); err != nil {
		t.Fatalf("parse json: %v", err)
	}
	if report.GeneratedAt == "" {
		t.Error("expected generated_at")
	}
	if report.RekipediaVersion == "" {
		t.Error("expected rekipedia_version")
	}
	if report.Issues == nil {
		t.Error("expected issues array")
	}
}

func TestWriteRefactorOutputsSummaryCounts(t *testing.T) {
	dir := t.TempDir()
	syms := []models.Symbol{
		wSym("GodClass", "class", "src/x.go"),
		wSym("dead_fn", "function", "src/util.go"),
	}
	var rels []models.Relationship
	for i := 0; i < 6; i++ {
		rels = append(rels, wRel(strings.Repeat("c", i+1), "GodClass", "calls"))
	}
	for i := 0; i < 5; i++ {
		rels = append(rels, wRel("GodClass", strings.Repeat("d", i+1), "calls"))
	}
	combined := wMakeResult(syms, rels, nil)
	combined.FilesSeen = []string{"src/x.go"}

	if err := WriteRefactorOutputs(combined, dir, "0.9.0", false); err != nil {
		t.Fatalf("WriteRefactorOutputs: %v", err)
	}

	data, _ := os.ReadFile(filepath.Join(dir, "refactor_report.json"))
	var report RefactorReport
	json.Unmarshal(data, &report) //nolint:errcheck
	if report.Summary.High < 1 {
		t.Errorf("expected summary.high >= 1, got %d", report.Summary.High)
	}
	if report.Summary.Low < 1 {
		t.Errorf("expected summary.low >= 1, got %d", report.Summary.Low)
	}
}

func TestWriteRefactorOutputsEmptyResult(t *testing.T) {
	dir := t.TempDir()
	combined := wMakeResult(nil, nil, nil)

	if err := WriteRefactorOutputs(combined, dir, "0.9.0", false); err != nil {
		t.Fatalf("WriteRefactorOutputs: %v", err)
	}

	md, _ := os.ReadFile(filepath.Join(dir, "REFACTOR.md"))
	if !strings.Contains(string(md), "0 issues") {
		t.Error("expected '0 issues' in REFACTOR.md")
	}

	data, _ := os.ReadFile(filepath.Join(dir, "refactor_report.json"))
	var report RefactorReport
	json.Unmarshal(data, &report) //nolint:errcheck
	if len(report.Issues) != 0 {
		t.Errorf("expected empty issues, got %d", len(report.Issues))
	}
	if report.Summary.High != 0 || report.Summary.Medium != 0 || report.Summary.Low != 0 {
		t.Errorf("expected zero summary counts, got %+v", report.Summary)
	}
}

func TestWriteRefactorOutputsCreatesOutputDir(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "deep", "output")
	combined := wMakeResult(nil, nil, nil)

	if err := WriteRefactorOutputs(combined, dir, "0.9.0", false); err != nil {
		t.Fatalf("WriteRefactorOutputs: %v", err)
	}
	if _, err := os.Stat(dir); err != nil {
		t.Errorf("output dir not created: %v", err)
	}
}

// ── helpers ───────────────────────────────────────────────────────────────────

func filterKind(issues []RefactorIssue, kind string) []RefactorIssue {
	var out []RefactorIssue
	for _, i := range issues {
		if i.Kind == kind {
			out = append(out, i)
		}
	}
	return out
}
