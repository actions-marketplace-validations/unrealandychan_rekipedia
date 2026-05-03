// Package graph provides dependency graph analysis utilities.
package graph

import (
	"sort"

	"github.com/unrealandychan/rekipedia/internal/models"
)

// GodNode represents a highly-connected symbol (high degree centrality).
type GodNode struct {
	Name   string  `json:"name"`
	Degree int     `json:"degree"`
	Score  float64 `json:"score"`
}

// GetGodNodes returns the top-N symbols by total degree (in + out).
// Mirrors Python graph_analysis.get_god_nodes().
func GetGodNodes(relationships []models.Relationship, topN int) []GodNode {
	// count degree for each node
	degree := make(map[string]int)
	for _, r := range relationships {
		degree[r.From]++
		degree[r.To]++
	}
	// build list
	type entry struct {
		name string
		deg  int
	}
	entries := make([]entry, 0, len(degree))
	for name, deg := range degree {
		entries = append(entries, entry{name, deg})
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].deg != entries[j].deg {
			return entries[i].deg > entries[j].deg
		}
		return entries[i].name < entries[j].name
	})
	maxDeg := 1
	if len(entries) > 0 && entries[0].deg > 0 {
		maxDeg = entries[0].deg
	}
	if topN > len(entries) {
		topN = len(entries)
	}
	result := make([]GodNode, topN)
	for i, e := range entries[:topN] {
		result[i] = GodNode{
			Name:   e.name,
			Degree: e.deg,
			Score:  float64(e.deg) / float64(maxDeg),
		}
	}
	return result
}
