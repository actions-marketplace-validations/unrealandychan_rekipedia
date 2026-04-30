package models

import "testing"

func TestDefaultLLMConfig(t *testing.T) {
	cfg := DefaultLLMConfig()
	if cfg.Model != "ollama/llama4" {
		t.Errorf("expected model ollama/llama4, got %s", cfg.Model)
	}
	if cfg.Temperature != 0.2 {
		t.Errorf("expected temperature 0.2, got %f", cfg.Temperature)
	}
}

func TestSymbolKindConstants(t *testing.T) {
	kinds := []SymbolKind{
		SymbolFunction, SymbolClass, SymbolType, SymbolVariable,
		SymbolInterface, SymbolEnum, SymbolModule, SymbolOther,
	}
	if len(kinds) != 8 {
		t.Errorf("expected 8 symbol kinds, got %d", len(kinds))
	}
}

func TestRelKindConstants(t *testing.T) {
	rels := []RelKind{RelImport, RelCall, RelInherits, RelUses, RelReExports}
	if len(rels) != 5 {
		t.Errorf("expected 5 rel kinds, got %d", len(rels))
	}
}

func TestAnalysisResultZeroValue(t *testing.T) {
	r := AnalysisResult{ShardID: "test"}
	if r.ShardID != "test" {
		t.Error("ShardID not set")
	}
	if r.Symbols != nil {
		t.Error("expected nil Symbols")
	}
	if r.Evidence != nil {
		t.Error("expected nil Evidence map")
	}
}

func TestWikiPlanZeroValue(t *testing.T) {
	plan := WikiPlan{IndexSlug: "index"}
	if plan.IndexSlug != "index" {
		t.Error("IndexSlug not set")
	}
}
