package graph

import (
	"testing"

	"github.com/unrealandychan/rekipedia/internal/models"
)

func TestGetGodNodes_Empty(t *testing.T) {
	result := GetGodNodes(nil, 10)
	if len(result) != 0 {
		t.Errorf("expected empty result, got %d nodes", len(result))
	}
}

func TestGetGodNodes_TopNLargerThanNodes(t *testing.T) {
	rels := []models.Relationship{
		{From: "A", To: "B", Kind: models.RelCall},
		{From: "B", To: "C", Kind: models.RelCall},
	}
	// 3 unique nodes: A, B, C; asking for topN=100 should return all 3
	result := GetGodNodes(rels, 100)
	if len(result) != 3 {
		t.Errorf("expected 3 nodes, got %d", len(result))
	}
}

func TestGetGodNodes_HighestDegreeFirst(t *testing.T) {
	rels := []models.Relationship{
		{From: "X", To: "Hub", Kind: models.RelCall},
		{From: "Y", To: "Hub", Kind: models.RelCall},
		{From: "Z", To: "Hub", Kind: models.RelCall},
		{From: "Hub", To: "Out", Kind: models.RelCall},
		{From: "Leaf", To: "Out", Kind: models.RelCall},
	}
	// Hub appears 4 times (3 incoming + 1 outgoing), Out appears 2 times
	result := GetGodNodes(rels, 3)
	if len(result) == 0 {
		t.Fatal("expected non-empty result")
	}
	if result[0].Name != "Hub" {
		t.Errorf("expected Hub as top node, got %s", result[0].Name)
	}
	if result[0].Score != 1.0 {
		t.Errorf("expected top node score=1.0, got %f", result[0].Score)
	}
	// verify descending order
	for i := 1; i < len(result); i++ {
		if result[i].Degree > result[i-1].Degree {
			t.Errorf("nodes not in descending degree order at index %d", i)
		}
	}
}
