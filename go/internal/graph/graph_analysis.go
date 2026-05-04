// Package graph provides dependency graph analysis utilities.
package graph

import (
	"fmt"
	"sort"
	"strings"

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

// HubNode represents a high-centrality node (hub or bridge).
type HubNode struct {
	Name      string `json:"name"`
	InDegree  int    `json:"in_degree"`
	OutDegree int    `json:"out_degree"`
	Score     int    `json:"score"`
	IsBridge  bool   `json:"is_bridge"`
}

// GetHubNodes finds top-N nodes by combined degree. IsBridge = in>=2 AND out>=2.
func GetHubNodes(relationships []models.Relationship, topN int) []HubNode {
	inDeg := make(map[string]int)
	outDeg := make(map[string]int)
	for _, r := range relationships {
		outDeg[r.From]++
		inDeg[r.To]++
	}
	all := make(map[string]struct{})
	for k := range inDeg {
		all[k] = struct{}{}
	}
	for k := range outDeg {
		all[k] = struct{}{}
	}

	nodes := make([]HubNode, 0, len(all))
	for name := range all {
		i, o := inDeg[name], outDeg[name]
		nodes = append(nodes, HubNode{
			Name: name, InDegree: i, OutDegree: o,
			Score: i + o, IsBridge: i >= 2 && o >= 2,
		})
	}
	sort.Slice(nodes, func(i, j int) bool { return nodes[i].Score > nodes[j].Score })
	if topN > len(nodes) {
		topN = len(nodes)
	}
	return nodes[:topN]
}

// KnowledgeGap represents a symbol with high call-count but no test coverage.
type KnowledgeGap struct {
	Name      string `json:"name"`
	CallCount int    `json:"call_count"`
	Kind      string `json:"kind"`
	Reason    string `json:"reason"`
}

// GetKnowledgeGaps returns symbols with call_count>=3 not covered by tests.
func GetKnowledgeGaps(relationships []models.Relationship, symbols []models.Symbol, topN int) []KnowledgeGap {
	callCount := make(map[string]int)
	testCovered := make(map[string]bool)

	for _, r := range relationships {
		if string(r.Kind) == "calls" {
			callCount[r.To]++
			if strings.HasPrefix(r.From, "test_") || strings.Contains(r.File, "test") {
				testCovered[r.To] = true
			}
		}
	}

	symKind := make(map[string]string)
	for _, s := range symbols {
		symKind[s.Name] = string(s.Kind)
	}

	var gaps []KnowledgeGap
	for name, count := range callCount {
		if count < 3 {
			continue
		}
		if testCovered[name] {
			continue
		}
		k := symKind[name]
		if k != "function" && k != "method" && k != "class" {
			continue
		}
		gaps = append(gaps, KnowledgeGap{
			Name: name, CallCount: count, Kind: k,
			Reason: fmt.Sprintf("called %d times, no test coverage", count),
		})
	}
	sort.Slice(gaps, func(i, j int) bool { return gaps[i].CallCount > gaps[j].CallCount })
	if topN > len(gaps) {
		topN = len(gaps)
	}
	return gaps[:topN]
}
