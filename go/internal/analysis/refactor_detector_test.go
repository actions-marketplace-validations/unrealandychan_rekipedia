package analysis

import (
	"testing"

	"github.com/unrealandychan/rekipedia/internal/config"
	"github.com/unrealandychan/rekipedia/internal/models"
)

var defaultCfg = config.DefaultRefactorConfig()

// ---------------------------------------------------------------------------
// DetectGodNodes
// ---------------------------------------------------------------------------

func TestDetectGodNodes_Empty(t *testing.T) {
	issues := DetectGodNodes(nil, nil, defaultCfg)
	if len(issues) != 0 {
		t.Fatalf("expected 0 issues, got %d", len(issues))
	}
}

func TestDetectGodNodes_DetectsHub(t *testing.T) {
	rels := make([]models.Relationship, 0)
	for i := 0; i < 15; i++ {
		rels = append(rels, models.Relationship{From: "hub", To: string(rune('a' + i)), Kind: "calls"})
	}
	for i := 0; i < 5; i++ {
		rels = append(rels, models.Relationship{From: string(rune('p' + i)), To: "hub", Kind: "calls"})
	}
	cfg := config.RefactorConfig{GodNodeTopPct: 0.1, HighFanIn: 20, HighFanOut: 15, DeepInheritanceDepth: 3}
	issues := DetectGodNodes(rels, nil, cfg)
	if len(issues) == 0 {
		t.Fatal("expected at least one god node")
	}
	if issues[0].Symbol != "hub" {
		t.Errorf("expected hub, got %s", issues[0].Symbol)
	}
	if issues[0].Kind != "god_class" {
		t.Errorf("expected god_class, got %s", issues[0].Kind)
	}
	if issues[0].Severity != "high" {
		t.Errorf("expected high severity, got %s", issues[0].Severity)
	}
}

func TestDetectGodNodes_MetricsPopulated(t *testing.T) {
	rels := []models.Relationship{
		{From: "a", To: "b", Kind: "calls"},
		{From: "c", To: "a", Kind: "calls"},
		{From: "a", To: "d", Kind: "calls"},
	}
	cfg := config.RefactorConfig{GodNodeTopPct: 1.0}
	issues := DetectGodNodes(rels, nil, cfg)
	var aIssue *RefactorIssue
	for i := range issues {
		if issues[i].Symbol == "a" {
			aIssue = &issues[i]
			break
		}
	}
	if aIssue == nil {
		t.Fatal("symbol a not found in issues")
	}
	if aIssue.Metrics["in_degree"] != 1 {
		t.Errorf("in_degree: expected 1, got %v", aIssue.Metrics["in_degree"])
	}
	if aIssue.Metrics["out_degree"] != 2 {
		t.Errorf("out_degree: expected 2, got %v", aIssue.Metrics["out_degree"])
	}
}

// ---------------------------------------------------------------------------
// DetectCircularDeps
// ---------------------------------------------------------------------------

func TestDetectCircularDeps_NoCycle(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "calls"},
		{From: "B", To: "C", Kind: "calls"},
	}
	issues := DetectCircularDeps(rels)
	if len(issues) != 0 {
		t.Fatalf("expected 0 issues, got %d", len(issues))
	}
}

func TestDetectCircularDeps_SimpleCycle(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "calls"},
		{From: "B", To: "C", Kind: "calls"},
		{From: "C", To: "A", Kind: "calls"},
	}
	issues := DetectCircularDeps(rels)
	if len(issues) != 1 {
		t.Fatalf("expected 1 cycle, got %d", len(issues))
	}
	if issues[0].Kind != "circular_dep" {
		t.Errorf("expected circular_dep, got %s", issues[0].Kind)
	}
	if issues[0].Severity != "high" {
		t.Errorf("expected high severity, got %s", issues[0].Severity)
	}
	if issues[0].Metrics["cycle_length"] != 3 {
		t.Errorf("expected cycle_length 3, got %v", issues[0].Metrics["cycle_length"])
	}
}

func TestDetectCircularDeps_TwoCyclesDeduplicated(t *testing.T) {
	// A->B->A and B->A->B are the same cycle
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "calls"},
		{From: "B", To: "A", Kind: "calls"},
	}
	issues := DetectCircularDeps(rels)
	if len(issues) != 1 {
		t.Errorf("expected 1 (deduplicated) cycle, got %d", len(issues))
	}
}

func TestDetectCircularDeps_SelfLoopExcluded(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "A", Kind: "calls"},
	}
	issues := DetectCircularDeps(rels)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues for self-loop, got %d", len(issues))
	}
}

// ---------------------------------------------------------------------------
// DetectDeadCode
// ---------------------------------------------------------------------------

func TestDetectDeadCode_PrivatePythonFlagged(t *testing.T) {
	syms := []models.Symbol{
		{Name: "_helper", Kind: "function", File: "utils.py"},
	}
	issues := DetectDeadCode(nil, syms)
	if len(issues) != 1 {
		t.Fatalf("expected 1 dead code issue, got %d", len(issues))
	}
	if issues[0].Symbol != "_helper" {
		t.Errorf("expected _helper, got %s", issues[0].Symbol)
	}
	if issues[0].Kind != "dead_code" {
		t.Errorf("expected dead_code, got %s", issues[0].Kind)
	}
	if issues[0].Severity != "low" {
		t.Errorf("expected low severity, got %s", issues[0].Severity)
	}
}

func TestDetectDeadCode_PublicPythonExcluded(t *testing.T) {
	syms := []models.Symbol{
		{Name: "helper", Kind: "function", File: "utils.py"},
	}
	issues := DetectDeadCode(nil, syms)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues for public Python symbol, got %d", len(issues))
	}
}

func TestDetectDeadCode_GoUnexportedFlagged(t *testing.T) {
	syms := []models.Symbol{
		{Name: "parseToken", Kind: "function", File: "parser.go"},
	}
	issues := DetectDeadCode(nil, syms)
	if len(issues) != 1 {
		t.Fatalf("expected 1 dead code issue, got %d", len(issues))
	}
}

func TestDetectDeadCode_GoExportedExcluded(t *testing.T) {
	syms := []models.Symbol{
		{Name: "ParseToken", Kind: "function", File: "parser.go"},
	}
	issues := DetectDeadCode(nil, syms)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues for exported Go symbol, got %d", len(issues))
	}
}

func TestDetectDeadCode_WithCallerExcluded(t *testing.T) {
	rels := []models.Relationship{
		{From: "caller", To: "_helper", Kind: "calls"},
	}
	syms := []models.Symbol{
		{Name: "_helper", Kind: "function", File: "utils.py"},
	}
	issues := DetectDeadCode(rels, syms)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues when symbol has callers, got %d", len(issues))
	}
}

// ---------------------------------------------------------------------------
// DetectHighFanIn
// ---------------------------------------------------------------------------

func TestDetectHighFanIn_Detected(t *testing.T) {
	cfg := config.RefactorConfig{HighFanIn: 3}
	rels := make([]models.Relationship, 5)
	for i := range rels {
		rels[i] = models.Relationship{From: string(rune('a' + i)), To: "hotfunc", Kind: "calls"}
	}
	issues := DetectHighFanIn(rels, nil, cfg)
	if len(issues) != 1 {
		t.Fatalf("expected 1 issue, got %d", len(issues))
	}
	if issues[0].Symbol != "hotfunc" {
		t.Errorf("expected hotfunc, got %s", issues[0].Symbol)
	}
	if issues[0].Kind != "high_fan_in" {
		t.Errorf("expected high_fan_in, got %s", issues[0].Kind)
	}
	if issues[0].Severity != "medium" {
		t.Errorf("expected medium, got %s", issues[0].Severity)
	}
	if issues[0].Metrics["in_degree"] != 5 {
		t.Errorf("expected in_degree 5, got %v", issues[0].Metrics["in_degree"])
	}
}

func TestDetectHighFanIn_BelowThreshold(t *testing.T) {
	cfg := config.RefactorConfig{HighFanIn: 10}
	rels := []models.Relationship{
		{From: "a", To: "f", Kind: "calls"},
		{From: "b", To: "f", Kind: "calls"},
	}
	issues := DetectHighFanIn(rels, nil, cfg)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues, got %d", len(issues))
	}
}

// ---------------------------------------------------------------------------
// DetectHighFanOut
// ---------------------------------------------------------------------------

func TestDetectHighFanOut_Detected(t *testing.T) {
	cfg := config.RefactorConfig{HighFanOut: 3}
	rels := make([]models.Relationship, 5)
	for i := range rels {
		rels[i] = models.Relationship{From: "bigfunc", To: string(rune('a' + i)), Kind: "calls"}
	}
	issues := DetectHighFanOut(rels, nil, cfg)
	if len(issues) != 1 {
		t.Fatalf("expected 1 issue, got %d", len(issues))
	}
	if issues[0].Symbol != "bigfunc" {
		t.Errorf("expected bigfunc, got %s", issues[0].Symbol)
	}
	if issues[0].Kind != "high_fan_out" {
		t.Errorf("expected high_fan_out, got %s", issues[0].Kind)
	}
	if issues[0].Severity != "medium" {
		t.Errorf("expected medium, got %s", issues[0].Severity)
	}
	if issues[0].Metrics["out_degree"] != 5 {
		t.Errorf("expected out_degree 5, got %v", issues[0].Metrics["out_degree"])
	}
}

func TestDetectHighFanOut_BelowThreshold(t *testing.T) {
	cfg := config.RefactorConfig{HighFanOut: 10}
	rels := []models.Relationship{
		{From: "f", To: "a", Kind: "calls"},
		{From: "f", To: "b", Kind: "calls"},
	}
	issues := DetectHighFanOut(rels, nil, cfg)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues, got %d", len(issues))
	}
}

// ---------------------------------------------------------------------------
// DetectDeepInheritance
// ---------------------------------------------------------------------------

func TestDetectDeepInheritance_Detected(t *testing.T) {
	// A inherits B, B inherits C, C inherits D → depth=3
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "inherits"},
		{From: "B", To: "C", Kind: "inherits"},
		{From: "C", To: "D", Kind: "inherits"},
	}
	cfg := config.RefactorConfig{DeepInheritanceDepth: 2}
	issues := DetectDeepInheritance(rels, nil, cfg)
	if len(issues) != 1 {
		t.Fatalf("expected 1 deep inheritance issue, got %d", len(issues))
	}
	if issues[0].Symbol != "A" {
		t.Errorf("expected A, got %s", issues[0].Symbol)
	}
	if issues[0].Kind != "deep_inheritance" {
		t.Errorf("expected deep_inheritance, got %s", issues[0].Kind)
	}
	if issues[0].Severity != "medium" {
		t.Errorf("expected medium, got %s", issues[0].Severity)
	}
	if issues[0].Metrics["depth"] != 3 {
		t.Errorf("expected depth 3, got %v", issues[0].Metrics["depth"])
	}
}

func TestDetectDeepInheritance_WithinThreshold(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "inherits"},
		{From: "B", To: "C", Kind: "inherits"},
	}
	cfg := config.RefactorConfig{DeepInheritanceDepth: 3}
	issues := DetectDeepInheritance(rels, nil, cfg)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues, got %d", len(issues))
	}
}

func TestDetectDeepInheritance_NonInheritsIgnored(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "calls"},
		{From: "B", To: "C", Kind: "calls"},
		{From: "C", To: "D", Kind: "calls"},
	}
	cfg := config.RefactorConfig{DeepInheritanceDepth: 1}
	issues := DetectDeepInheritance(rels, nil, cfg)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues (non-inherits edges), got %d", len(issues))
	}
}

func TestDetectDeepInheritance_ChainInMetrics(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: "inherits"},
		{From: "B", To: "C", Kind: "inherits"},
		{From: "C", To: "D", Kind: "inherits"},
	}
	cfg := config.RefactorConfig{DeepInheritanceDepth: 2}
	issues := DetectDeepInheritance(rels, nil, cfg)
	chain, ok := issues[0].Metrics["chain"].(string)
	if !ok || chain == "" {
		t.Errorf("expected chain in metrics, got %v", issues[0].Metrics["chain"])
	}
}

// ---------------------------------------------------------------------------
// DetectAll
// ---------------------------------------------------------------------------

func TestDetectAll_ReturnsMultipleKinds(t *testing.T) {
	rels := []models.Relationship{
		// circular dep
		{From: "X", To: "Y", Kind: "calls"},
		{From: "Y", To: "X", Kind: "calls"},
	}
	// add high fan-in
	for i := 0; i < 25; i++ {
		rels = append(rels, models.Relationship{
			From: string(rune('a'+i%26)) + "caller",
			To:   "hotfunc",
			Kind: "calls",
		})
	}
	syms := []models.Symbol{
		{Name: "_dead", Kind: "function", File: "utils.py"},
	}
	cfg := config.RefactorConfig{
		GodNodeTopPct:        0.5,
		HighFanIn:            20,
		HighFanOut:           15,
		DeepInheritanceDepth: 3,
	}
	issues := DetectAll(rels, syms, cfg)
	kinds := make(map[string]bool)
	for _, i := range issues {
		kinds[i.Kind] = true
	}
	if !kinds["circular_dep"] {
		t.Error("expected circular_dep in results")
	}
	if !kinds["dead_code"] {
		t.Error("expected dead_code in results")
	}
	if !kinds["high_fan_in"] {
		t.Error("expected high_fan_in in results")
	}
}

func TestDetectAll_EmptyInput(t *testing.T) {
	issues := DetectAll(nil, nil, defaultCfg)
	if len(issues) != 0 {
		t.Errorf("expected 0 issues for empty input, got %d", len(issues))
	}
}
