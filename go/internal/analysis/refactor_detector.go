// Package analysis provides graph-based static analysis metrics for refactoring detection.
// It analyses the symbol/relationship graph built by reki scan to detect code smells
// without requiring an LLM — pure graph metrics.
package analysis

import (
	"sort"
	"strings"

	"github.com/unrealandychan/rekipedia/internal/config"
	"github.com/unrealandychan/rekipedia/internal/models"
)

// RefactorIssue represents a single detected refactoring issue.
type RefactorIssue struct {
	Kind     string                 `json:"kind"`     // "god_class" | "circular_dep" | "dead_code" | "high_fan_in" | "high_fan_out" | "deep_inheritance"
	Symbol   string                 `json:"symbol"`   // affected symbol name
	File     string                 `json:"file"`
	Severity string                 `json:"severity"` // "high" | "medium" | "low"
	Metrics  map[string]interface{} `json:"metrics"`  // raw numbers (degree, depth, etc.)
	Callers  []string               `json:"callers"`  // affected callers / dependents
}

// isExported returns true if the symbol is considered exported/public.
// Go (.go files): exported = first letter uppercase.
// Python and other languages: public = name does not start with "_".
func isExported(name, file string) bool {
	if name == "" {
		return true
	}
	if strings.HasSuffix(file, ".go") {
		return name[0] >= 'A' && name[0] <= 'Z'
	}
	return !strings.HasPrefix(name, "_")
}

// DetectGodNodes finds god classes/functions: top cfg.GodNodeTopPct of nodes by total degree.
func DetectGodNodes(relationships []models.Relationship, symbols []models.Symbol, cfg config.RefactorConfig) []RefactorIssue {
	inDeg := make(map[string]int)
	outDeg := make(map[string]int)
	callersOf := make(map[string][]string)

	for _, r := range relationships {
		outDeg[r.From]++
		inDeg[r.To]++
		callersOf[r.To] = append(callersOf[r.To], r.From)
	}

	all := make(map[string]struct{})
	for k := range inDeg {
		all[k] = struct{}{}
	}
	for k := range outDeg {
		all[k] = struct{}{}
	}
	if len(all) == 0 {
		return nil
	}

	type entry struct {
		name  string
		total int
	}
	entries := make([]entry, 0, len(all))
	for name := range all {
		entries = append(entries, entry{name, inDeg[name] + outDeg[name]})
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].total != entries[j].total {
			return entries[i].total > entries[j].total
		}
		return entries[i].name < entries[j].name
	})

	symFile := make(map[string]string)
	for _, s := range symbols {
		symFile[s.Name] = s.File
	}

	threshold := int(float64(len(entries)) * cfg.GodNodeTopPct)
	if threshold < 1 {
		threshold = 1
	}
	if threshold > len(entries) {
		threshold = len(entries)
	}

	issues := make([]RefactorIssue, 0, threshold)
	for _, e := range entries[:threshold] {
		callers := callersOf[e.name]
		if callers == nil {
			callers = []string{}
		}
		issues = append(issues, RefactorIssue{
			Kind:     "god_class",
			Symbol:   e.name,
			File:     symFile[e.name],
			Severity: "high",
			Metrics: map[string]interface{}{
				"in_degree":    inDeg[e.name],
				"out_degree":   outDeg[e.name],
				"total_degree": e.total,
			},
			Callers: callers,
		})
	}
	return issues
}

// DetectCircularDeps detects circular dependencies using iterative DFS.
func DetectCircularDeps(relationships []models.Relationship) []RefactorIssue {
	graph := make(map[string][]string)
	allNodes := make(map[string]struct{})

	for _, r := range relationships {
		if r.From != r.To {
			graph[r.From] = append(graph[r.From], r.To)
			allNodes[r.From] = struct{}{}
			allNodes[r.To] = struct{}{}
		}
	}
	// Sort adjacency lists for deterministic output
	for k := range graph {
		sort.Strings(graph[k])
	}

	visited := make(map[string]bool)
	inStack := make(map[string]bool)
	path := make([]string, 0)
	var foundCycles [][]string
	seenCycles := make(map[string]bool)

	var dfs func(node string)
	dfs = func(node string) {
		visited[node] = true
		inStack[node] = true
		path = append(path, node)

		for _, neighbor := range graph[node] {
			if !visited[neighbor] {
				dfs(neighbor)
			} else if inStack[neighbor] {
				// Locate cycle start in current path
				idx := -1
				for i, p := range path {
					if p == neighbor {
						idx = i
						break
					}
				}
				if idx >= 0 {
					cycle := make([]string, len(path)-idx)
					copy(cycle, path[idx:])
					// Normalize: rotate so lexicographically smallest node is first
					minIdx := 0
					for i, n := range cycle {
						if n < cycle[minIdx] {
							minIdx = i
						}
					}
					normalized := append(append([]string{}, cycle[minIdx:]...), cycle[:minIdx]...)
					key := strings.Join(normalized, "->")
					if !seenCycles[key] {
						seenCycles[key] = true
						saved := make([]string, len(cycle))
						copy(saved, cycle)
						foundCycles = append(foundCycles, saved)
					}
				}
			}
		}

		path = path[:len(path)-1]
		inStack[node] = false
	}

	nodes := make([]string, 0, len(allNodes))
	for n := range allNodes {
		nodes = append(nodes, n)
	}
	sort.Strings(nodes)

	for _, n := range nodes {
		if !visited[n] {
			dfs(n)
		}
	}

	issues := make([]RefactorIssue, 0, len(foundCycles))
	for _, cycle := range foundCycles {
		cycleStr := strings.Join(cycle, " -> ") + " -> " + cycle[0]
		callers := []string{}
		if len(cycle) > 1 {
			callers = cycle[1:]
		}
		issues = append(issues, RefactorIssue{
			Kind:     "circular_dep",
			Symbol:   cycle[0],
			File:     "",
			Severity: "high",
			Metrics: map[string]interface{}{
				"cycle_length": len(cycle),
				"cycle":        cycleStr,
			},
			Callers: callers,
		})
	}
	return issues
}

// DetectDeadCode finds symbols with zero in-degree that are not exported/public.
func DetectDeadCode(relationships []models.Relationship, symbols []models.Symbol) []RefactorIssue {
	inDeg := make(map[string]int)
	for _, r := range relationships {
		inDeg[r.To]++
	}

	var issues []RefactorIssue
	for _, sym := range symbols {
		if inDeg[sym.Name] > 0 {
			continue
		}
		if isExported(sym.Name, sym.File) {
			continue
		}
		issues = append(issues, RefactorIssue{
			Kind:     "dead_code",
			Symbol:   sym.Name,
			File:     sym.File,
			Severity: "low",
			Metrics: map[string]interface{}{
				"in_degree": 0,
				"kind":      string(sym.Kind),
			},
			Callers: []string{},
		})
	}
	return issues
}

// DetectHighFanIn finds symbols with more than cfg.HighFanIn callers.
func DetectHighFanIn(relationships []models.Relationship, symbols []models.Symbol, cfg config.RefactorConfig) []RefactorIssue {
	inDeg := make(map[string]int)
	callersOf := make(map[string][]string)

	for _, r := range relationships {
		inDeg[r.To]++
		if r.From != "" {
			callersOf[r.To] = append(callersOf[r.To], r.From)
		}
	}

	symFile := make(map[string]string)
	for _, s := range symbols {
		symFile[s.Name] = s.File
	}

	var issues []RefactorIssue
	// Sort keys for deterministic output
	names := make([]string, 0, len(inDeg))
	for n := range inDeg {
		names = append(names, n)
	}
	sort.Strings(names)

	for _, name := range names {
		count := inDeg[name]
		if count > cfg.HighFanIn {
			callers := callersOf[name]
			if callers == nil {
				callers = []string{}
			}
			issues = append(issues, RefactorIssue{
				Kind:     "high_fan_in",
				Symbol:   name,
				File:     symFile[name],
				Severity: "medium",
				Metrics:  map[string]interface{}{"in_degree": count},
				Callers:  callers,
			})
		}
	}
	return issues
}

// DetectHighFanOut finds symbols with more than cfg.HighFanOut dependencies.
func DetectHighFanOut(relationships []models.Relationship, symbols []models.Symbol, cfg config.RefactorConfig) []RefactorIssue {
	outDeg := make(map[string]int)
	depsOf := make(map[string][]string)

	for _, r := range relationships {
		outDeg[r.From]++
		if r.To != "" {
			depsOf[r.From] = append(depsOf[r.From], r.To)
		}
	}

	symFile := make(map[string]string)
	for _, s := range symbols {
		symFile[s.Name] = s.File
	}

	var issues []RefactorIssue
	names := make([]string, 0, len(outDeg))
	for n := range outDeg {
		names = append(names, n)
	}
	sort.Strings(names)

	for _, name := range names {
		count := outDeg[name]
		if count > cfg.HighFanOut {
			deps := depsOf[name]
			if deps == nil {
				deps = []string{}
			}
			issues = append(issues, RefactorIssue{
				Kind:     "high_fan_out",
				Symbol:   name,
				File:     symFile[name],
				Severity: "medium",
				Metrics:  map[string]interface{}{"out_degree": count},
				Callers:  deps,
			})
		}
	}
	return issues
}

// DetectDeepInheritance finds classes with inheritance depth > cfg.DeepInheritanceDepth.
func DetectDeepInheritance(relationships []models.Relationship, symbols []models.Symbol, cfg config.RefactorConfig) []RefactorIssue {
	// child -> parents
	inheritsGraph := make(map[string][]string)
	for _, r := range relationships {
		if string(r.Kind) == "inherits" && r.From != "" && r.To != "" {
			inheritsGraph[r.From] = append(inheritsGraph[r.From], r.To)
		}
	}

	symFile := make(map[string]string)
	for _, s := range symbols {
		symFile[s.Name] = s.File
	}

	// Memoized depth computation
	depthCache := make(map[string]int)
	var computeDepth func(name string, visiting map[string]bool) int
	computeDepth = func(name string, visiting map[string]bool) int {
		if d, ok := depthCache[name]; ok {
			return d
		}
		if visiting[name] {
			return 0 // cycle guard
		}
		parents := inheritsGraph[name]
		if len(parents) == 0 {
			depthCache[name] = 0
			return 0
		}
		visiting[name] = true
		maxParent := 0
		for _, p := range parents {
			if d := computeDepth(p, visiting); d > maxParent {
				maxParent = d
			}
		}
		delete(visiting, name)
		d := 1 + maxParent
		depthCache[name] = d
		return d
	}

	// Sort keys for determinism
	names := make([]string, 0, len(inheritsGraph))
	for n := range inheritsGraph {
		names = append(names, n)
	}
	sort.Strings(names)

	var issues []RefactorIssue
	for _, name := range names {
		depth := computeDepth(name, make(map[string]bool))
		if depth > cfg.DeepInheritanceDepth {
			// Walk first-parent chain for display
			chain := []string{name}
			node := name
			for i := 0; i < depth; i++ {
				parents := inheritsGraph[node]
				if len(parents) == 0 {
					break
				}
				node = parents[0]
				chain = append(chain, node)
			}
			issues = append(issues, RefactorIssue{
				Kind:     "deep_inheritance",
				Symbol:   name,
				File:     symFile[name],
				Severity: "medium",
				Metrics: map[string]interface{}{
					"depth": depth,
					"chain": strings.Join(chain, " -> "),
				},
				Callers: []string{},
			})
		}
	}
	return issues
}

// DetectAll runs all refactor checks and returns the combined list of issues.
func DetectAll(relationships []models.Relationship, symbols []models.Symbol, cfg config.RefactorConfig) []RefactorIssue {
	var issues []RefactorIssue
	issues = append(issues, DetectGodNodes(relationships, symbols, cfg)...)
	issues = append(issues, DetectCircularDeps(relationships)...)
	issues = append(issues, DetectDeadCode(relationships, symbols)...)
	issues = append(issues, DetectHighFanIn(relationships, symbols, cfg)...)
	issues = append(issues, DetectHighFanOut(relationships, symbols, cfg)...)
	issues = append(issues, DetectDeepInheritance(relationships, symbols, cfg)...)
	return issues
}
