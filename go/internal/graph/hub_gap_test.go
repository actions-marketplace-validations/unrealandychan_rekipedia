package graph

import (
	"testing"

	"github.com/unrealandychan/rekipedia/internal/models"
)

func TestGetHubNodes(t *testing.T) {
	rels := []models.Relationship{
		{From: "a", To: "b", Kind: "calls"},
		{From: "c", To: "b", Kind: "calls"},
		{From: "b", To: "d", Kind: "calls"},
		{From: "b", To: "e", Kind: "calls"},
	}
	hubs := GetHubNodes(rels, 5)
	if len(hubs) == 0 {
		t.Fatal("expected hub nodes")
	}
	for _, h := range hubs {
		if h.Name == "b" {
			if !h.IsBridge {
				t.Error("b should be a bridge node")
			}
			return
		}
	}
	t.Error("b not found in hub nodes")
}

func TestGetKnowledgeGaps(t *testing.T) {
	rels := []models.Relationship{
		{From: "caller1", To: "hotFunc", Kind: "calls"},
		{From: "caller2", To: "hotFunc", Kind: "calls"},
		{From: "caller3", To: "hotFunc", Kind: "calls"},
	}
	syms := []models.Symbol{
		{Name: "hotFunc", Kind: "function"},
	}
	gaps := GetKnowledgeGaps(rels, syms, 10)
	if len(gaps) == 0 {
		t.Fatal("expected knowledge gaps")
	}
	if gaps[0].Name != "hotFunc" {
		t.Errorf("expected hotFunc, got %s", gaps[0].Name)
	}
}
