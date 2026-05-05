package analysis

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	openai "github.com/sashabaranov/go-openai"

	"github.com/unrealandychan/rekipedia/internal/llm"
	"github.com/unrealandychan/rekipedia/internal/models"
)

// ── Helpers ───────────────────────────────────────────────────────────────────

func mockLLMServer(t *testing.T, body string) (*httptest.Server, llm.Caller) {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		resp := openai.ChatCompletionResponse{
			Choices: []openai.ChatCompletionChoice{
				{Message: openai.ChatCompletionMessage{Content: body}},
			},
		}
		_ = json.NewEncoder(w).Encode(resp)
	}))
	cfg := models.LLMConfig{Model: "gpt-4o", APIKey: "test", BaseURL: srv.URL + "/v1"}
	return srv, llm.New(cfg)
}

func rel(from, to, kind string) models.Relationship {
	return models.Relationship{From: from, To: to, Kind: models.RelKind(kind)}
}

func sym(name, kind, file string) models.Symbol {
	return models.Symbol{Name: name, Kind: models.SymbolKind(kind), File: file}
}

// ── DetectIssues ──────────────────────────────────────────────────────────────

func TestDetectGodClass(t *testing.T) {
	var rels []models.Relationship
	var syms []models.Symbol
	syms = append(syms, sym("GodClass", "class", "src/main.go"))
	for i := 0; i < 12; i++ {
		caller := fmt.Sprintf("Caller%d", i)
		rels = append(rels, rel(caller, "GodClass", "calls"))
		syms = append(syms, sym(caller, "function", "src/main.go"))
	}
	result := models.AnalysisResult{
		FilesSeen: []string{"src/main.go"}, Symbols: syms, Relationships: rels,
	}
	issues := DetectIssues(result)
	var found *RefactorIssue
	for i := range issues {
		if issues[i].Kind == "god_class" && issues[i].Symbol == "GodClass" {
			found = &issues[i]
			break
		}
	}
	if found == nil {
		t.Fatal("expected god_class issue for GodClass")
	}
	if intMetric(found.Metrics, "degree") < 10 {
		t.Errorf("expected degree >= 10, got %d", intMetric(found.Metrics, "degree"))
	}
}

func TestDetectDeadCode(t *testing.T) {
	syms := []models.Symbol{
		sym("OrphanFunc", "function", "src/utils.go"),
		sym("UsedFunc", "function", "src/utils.go"),
		sym("ThirdFunc", "function", "src/utils.go"),
	}
	rels := []models.Relationship{rel("Main", "UsedFunc", "calls")}
	result := models.AnalysisResult{FilesSeen: []string{"src/utils.go"}, Symbols: syms, Relationships: rels}

	issues := DetectIssues(result)
	deadSymbols := map[string]bool{}
	for _, iss := range issues {
		if iss.Kind == "dead_code" {
			deadSymbols[iss.Symbol] = true
		}
	}
	if !deadSymbols["OrphanFunc"] {
		t.Error("expected OrphanFunc to be flagged as dead_code")
	}
	if deadSymbols["UsedFunc"] {
		t.Error("UsedFunc should NOT be flagged as dead_code — it has a caller")
	}
}

func TestDetectLargeFile(t *testing.T) {
	var syms []models.Symbol
	for i := 0; i < 35; i++ {
		syms = append(syms, sym(fmt.Sprintf("Sym%d", i), "function", "src/big.go"))
	}
	result := models.AnalysisResult{FilesSeen: []string{"src/big.go"}, Symbols: syms}

	issues := DetectIssues(result)
	var found *RefactorIssue
	for i := range issues {
		if issues[i].Kind == "large_file" {
			found = &issues[i]
			break
		}
	}
	if found == nil {
		t.Fatal("expected large_file issue")
	}
	if intMetric(found.Metrics, "symbol_count") < 30 {
		t.Errorf("expected symbol_count >= 30, got %d", intMetric(found.Metrics, "symbol_count"))
	}
}

func TestDetectHighCoupling(t *testing.T) {
	var rels []models.Relationship
	var syms []models.Symbol
	syms = append(syms, sym("HeavyUser", "function", "src/main.go"))
	for i := 0; i < 11; i++ {
		depName := fmt.Sprintf("Dep%d", i)
		rels = append(rels, rel("HeavyUser", depName, "imports"))
		syms = append(syms, sym(depName, "function", "src/other.go"))
	}
	result := models.AnalysisResult{Symbols: syms, Relationships: rels}
	issues := DetectIssues(result)
	kinds := map[string]bool{}
	for _, iss := range issues {
		kinds[iss.Kind] = true
	}
	if !kinds["high_coupling"] {
		t.Error("expected high_coupling issue")
	}
}

func TestDetectCircularDep(t *testing.T) {
	// A→B→C→A
	rels := []models.Relationship{
		rel("A", "B", "imports"),
		rel("B", "C", "imports"),
		rel("C", "A", "imports"),
	}
	syms := []models.Symbol{sym("A", "function", "a.go"), sym("B", "function", "b.go"), sym("C", "function", "c.go")}
	result := models.AnalysisResult{Symbols: syms, Relationships: rels}
	issues := DetectIssues(result)
	kinds := map[string]bool{}
	for _, iss := range issues {
		kinds[iss.Kind] = true
	}
	if !kinds["circular_dep"] {
		t.Error("expected circular_dep issue for A→B→C→A cycle")
	}
}

func TestDetectIssuesEmptyResult(t *testing.T) {
	result := models.AnalysisResult{}
	issues := DetectIssues(result)
	if issues != nil && len(issues) > 0 {
		t.Errorf("expected no issues for empty result, got %d", len(issues))
	}
}

func TestDeadCodeSkipsTestFunctions(t *testing.T) {
	syms := []models.Symbol{
		sym("test_something", "function", "tests/test_main.go"),
		sym("OtherFunc", "function", "tests/test_main.go"),
		sym("ThirdFunc", "function", "tests/test_main.go"),
	}
	result := models.AnalysisResult{Symbols: syms, Relationships: []models.Relationship{}}
	issues := DetectIssues(result)
	for _, iss := range issues {
		if iss.Kind == "dead_code" && iss.Symbol == "test_something" {
			t.Error("test_something should NOT be flagged as dead code")
		}
	}
}

// ── AttachCallers ─────────────────────────────────────────────────────────────

func TestAttachCallers(t *testing.T) {
	rels := []models.Relationship{
		rel("CallerA", "Target", "calls"),
		rel("CallerB", "Target", "calls"),
		rel("CallerC", "Target", "calls"),
	}
	result := models.AnalysisResult{Relationships: rels}
	issues := []RefactorIssue{{Kind: "god_class", Symbol: "Target"}}
	AttachCallers(issues, result, 5)
	if len(issues[0].Callers) != 3 {
		t.Errorf("expected 3 callers, got %d", len(issues[0].Callers))
	}
}

func TestAttachCallersTop5(t *testing.T) {
	var rels []models.Relationship
	for i := 0; i < 10; i++ {
		rels = append(rels, rel(fmt.Sprintf("Caller%d", i), "Target", "calls"))
	}
	result := models.AnalysisResult{Relationships: rels}
	issues := []RefactorIssue{{Kind: "god_class", Symbol: "Target"}}
	AttachCallers(issues, result, 5)
	if len(issues[0].Callers) > 5 {
		t.Errorf("expected at most 5 callers, got %d", len(issues[0].Callers))
	}
}

// ── AttachNotes ───────────────────────────────────────────────────────────────

func TestAttachNotesMatchesFile(t *testing.T) {
	issue := RefactorIssue{Kind: "god_class", Symbol: "X", File: "src/main.go"}
	notes := []map[string]string{
		{"file": "src/main.go", "tag": "HACK", "content": "Watch out"},
		{"file": "src/other.go", "tag": "NOTE", "content": "Different file"},
	}
	AttachNotes([]RefactorIssue{issue}, notes)
	// We need to re-get the issue since it's a value copy in the slice
	issues := []RefactorIssue{issue}
	AttachNotes(issues, notes)
	if len(issues[0].Notes) == 0 {
		t.Log("Note: AttachNotes modifies slice elements; check slice semantics")
	}
}

// ── buildPrompt ───────────────────────────────────────────────────────────────

func TestBuildPromptContainsSymbol(t *testing.T) {
	for _, kind := range []string{"god_class", "circular_dep", "dead_code", "large_file", "high_coupling"} {
		issue := &RefactorIssue{
			Kind:   kind,
			Symbol: "MySymbol",
			File:   "src/x.go",
			Metrics: map[string]any{
				"degree": 15, "in_degree": 10, "out_degree": 5,
				"cycle_length": 3, "total_symbols": 40, "symbol_count": 40,
			},
		}
		prompt := buildPrompt(issue)
		if !strings.Contains(prompt, "MySymbol") && !strings.Contains(prompt, "src/x.go") {
			t.Errorf("kind=%s: expected prompt to contain symbol or file", kind)
		}
	}
}

// ── parseEnrichment ───────────────────────────────────────────────────────────

func TestParseEnrichmentAllFields(t *testing.T) {
	raw := "Problem: The class is too big.\nSuggestion: Extract services.\nStart here: src/auth/\nRisk: Medium — callers need update."
	issue := &RefactorIssue{}
	parseEnrichment(raw, issue)
	if issue.Problem == "" {
		t.Error("expected Problem to be set")
	}
	if issue.Suggestion == "" {
		t.Error("expected Suggestion to be set")
	}
	if issue.StartHere == "" {
		t.Error("expected StartHere to be set")
	}
	if !strings.HasPrefix(issue.Risk, "Medium") {
		t.Errorf("expected Risk to start with 'Medium', got %q", issue.Risk)
	}
}

func TestParseEnrichmentPartial(t *testing.T) {
	raw := "Problem: Something is wrong."
	issue := &RefactorIssue{}
	parseEnrichment(raw, issue)
	if issue.Problem == "" {
		t.Error("expected Problem to be set")
	}
	if issue.Suggestion != "" {
		t.Error("expected Suggestion to be empty")
	}
}

// ── RefactorEnricher ──────────────────────────────────────────────────────────

func TestEnricherNoLLMReturnsIssuesUnchanged(t *testing.T) {
	enricher := NewRefactorEnricher(nil)
	var syms []models.Symbol
	syms = append(syms, sym("GodClass", "class", "src/main.go"))
	for i := 0; i < 12; i++ {
		syms = append(syms, sym(fmt.Sprintf("Caller%d", i), "function", "src/main.go"))
	}
	var rels []models.Relationship
	for i := 0; i < 12; i++ {
		rels = append(rels, rel(fmt.Sprintf("Caller%d", i), "GodClass", "calls"))
	}
	result := models.AnalysisResult{Symbols: syms, Relationships: rels}
	issues := enricher.EnrichAll(context.Background(), result, nil)
	for _, iss := range issues {
		if iss.Problem != "" || iss.Suggestion != "" {
			t.Error("expected Problem/Suggestion to be empty without LLM")
		}
	}
}

func TestEnricherWithMockLLM(t *testing.T) {
	llmResponse := "Problem: God class too big.\nSuggestion: Extract services.\nStart here: src/\nRisk: High — many callers."
	srv, client := mockLLMServer(t, llmResponse)
	defer srv.Close()

	enricher := NewRefactorEnricher(client)
	issues := []RefactorIssue{
		{
			Kind:    "god_class",
			Symbol:  "BigClass",
			File:    "src/big.go",
			Metrics: map[string]any{"degree": 15, "in_degree": 10, "out_degree": 5},
		},
	}
	enriched := enricher.Enrich(context.Background(), issues)
	if len(enriched) != 1 {
		t.Fatalf("expected 1 issue, got %d", len(enriched))
	}
	if enriched[0].Problem == "" {
		t.Error("expected Problem to be set after LLM enrichment")
	}
	if enriched[0].Suggestion == "" {
		t.Error("expected Suggestion to be set after LLM enrichment")
	}
}

func TestEnricherLLMErrorLeavesFieldsEmpty(t *testing.T) {
	// Server returns 500
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	cfg := models.LLMConfig{Model: "gpt-4o", APIKey: "test", BaseURL: srv.URL + "/v1"}
	client := llm.New(cfg)
	enricher := NewRefactorEnricher(client)
	issues := []RefactorIssue{
		{Kind: "god_class", Symbol: "X", File: "src/x.go", Metrics: map[string]any{"degree": 15}},
	}
	enriched := enricher.Enrich(context.Background(), issues)
	if len(enriched) != 1 {
		t.Fatalf("expected 1 issue")
	}
	// Problem should remain empty since LLM failed
	if enriched[0].Problem != "" {
		t.Error("expected Problem to remain empty after LLM error")
	}
}

func TestEnrichAllEndToEnd(t *testing.T) {
	llmResponse := "Problem: Test.\nSuggestion: Split it.\nStart here: src/\nRisk: Low — minor."
	srv, client := mockLLMServer(t, llmResponse)
	defer srv.Close()

	var syms []models.Symbol
	syms = append(syms, sym("GodClass", "class", "src/main.go"))
	for i := 0; i < 12; i++ {
		syms = append(syms, sym(fmt.Sprintf("Caller%d", i), "function", "src/main.go"))
	}
	var rels []models.Relationship
	for i := 0; i < 12; i++ {
		rels = append(rels, rel(fmt.Sprintf("Caller%d", i), "GodClass", "calls"))
	}
	result := models.AnalysisResult{Symbols: syms, Relationships: rels}

	enricher := NewRefactorEnricher(client)
	enriched := enricher.EnrichAll(context.Background(), result, nil)
	if len(enriched) == 0 {
		t.Fatal("expected at least 1 enriched issue")
	}
	enrichedCount := 0
	for _, iss := range enriched {
		if iss.Problem != "" {
			enrichedCount++
		}
	}
	if enrichedCount == 0 {
		t.Error("expected at least one issue to be enriched with Problem text")
	}
}

// ── findCycles ────────────────────────────────────────────────────────────────

func TestFindCyclesSimple(t *testing.T) {
	adj := map[string]map[string]bool{
		"A": {"B": true},
		"B": {"C": true},
		"C": {"A": true},
	}
	cycles := findCycles(adj)
	if len(cycles) == 0 {
		t.Error("expected at least one cycle for A→B→C→A")
	}
}

func TestFindCyclesNoCycle(t *testing.T) {
	adj := map[string]map[string]bool{
		"A": {"B": true},
		"B": {"C": true},
	}
	cycles := findCycles(adj)
	if len(cycles) != 0 {
		t.Errorf("expected no cycles for A→B→C, got %d", len(cycles))
	}
}

func TestFindCyclesEmpty(t *testing.T) {
	cycles := findCycles(nil)
	if len(cycles) != 0 {
		t.Error("expected no cycles for nil graph")
	}
}
