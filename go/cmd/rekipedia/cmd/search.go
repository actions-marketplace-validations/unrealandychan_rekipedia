package cmd

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"unicode"

	"github.com/spf13/cobra"
	"github.com/unrealandychan/rekipedia/internal/storage"
)

var searchFlags struct {
	outputDir string
	kind      string
}

// tokenizeSymbol splits a symbol name on snake_case and camelCase boundaries.
func tokenizeSymbol(name string) []string {
	// Replace hyphens with underscores and split on underscores first
	name = strings.ReplaceAll(name, "-", "_")
	parts := strings.Split(name, "_")
	var tokens []string
	camelRe := regexp.MustCompile(`[A-Z][a-z]+|[A-Z]+(?:[A-Z][a-z]|\d|\b)|[a-z]+|\d+`)
	for _, p := range parts {
		if p == "" {
			continue
		}
		// Check if it needs camelCase splitting
		hasCamel := false
		for _, r := range p {
			if unicode.IsUpper(r) {
				hasCamel = true
				break
			}
		}
		if hasCamel {
			matches := camelRe.FindAllString(p, -1)
			for _, m := range matches {
				tokens = append(tokens, strings.ToLower(m))
			}
		} else {
			tokens = append(tokens, strings.ToLower(p))
		}
	}
	if len(tokens) == 0 {
		tokens = []string{strings.ToLower(name)}
	}
	return tokens
}

// scoreBM25 computes a simple BM25-inspired score.
func scoreBM25(queryTokens, symbolTokens []string) float64 {
	k1, b, avgdl := 1.5, 0.75, 5.0
	dl := float64(len(symbolTokens))
	tfMap := make(map[string]int)
	for _, t := range symbolTokens {
		tfMap[t]++
	}
	var score float64
	for _, qt := range queryTokens {
		tf := float64(tfMap[qt])
		if tf == 0 {
			continue
		}
		idf := 1.0
		score += idf * (tf * (k1 + 1)) / (tf + k1*(1-b+b*dl/avgdl))
	}
	return score
}

var searchCmd = &cobra.Command{
	Use:   "search <query>",
	Short: "Search symbols in the codebase graph",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		query := args[0]
		queryTokens := tokenizeSymbol(query)
		dbPath := storage.DefaultPath(searchFlags.outputDir)
		store, err := storage.Open(dbPath)
		if err != nil {
			return fmt.Errorf("open store: %w", err)
		}
		defer store.Close()

		runID, err := store.LatestRunID(searchFlags.outputDir)
		if err != nil || runID == "" {
			return fmt.Errorf("no scan found — run reki scan first")
		}

		symbols, err := store.ListSymbols(runID)
		if err != nil {
			return err
		}

		type result struct {
			name  string
			kind  string
			file  string
			score float64
		}
		var results []result
		for _, s := range symbols {
			// Apply kind filter
			if searchFlags.kind != "" && string(s.Kind) != searchFlags.kind {
				continue
			}
			symbolTokens := tokenizeSymbol(s.Name)
			score := scoreBM25(queryTokens, symbolTokens)
			if score > 0 {
				results = append(results, result{s.Name, string(s.Kind), s.File, score})
			}
		}

		sort.Slice(results, func(i, j int) bool {
			return results[i].score > results[j].score
		})

		if len(results) == 0 {
			fmt.Printf("No results for %q\n", args[0])
			return nil
		}

		fmt.Printf("%-40s %-12s %s\n", "Name", "Kind", "File")
		fmt.Println(strings.Repeat("-", 80))
		cap := 50
		if len(results) < cap {
			cap = len(results)
		}
		for _, r := range results[:cap] {
			fmt.Printf("%-40s %-12s %s\n", r.name, r.kind, r.file)
		}
		fmt.Printf("\n%d result(s)\n", len(results))
		return nil
	},
}

func init() {
	searchCmd.Flags().StringVar(&searchFlags.outputDir, "output-dir", ".", "Directory with .rekipedia/")
	searchCmd.Flags().StringVar(&searchFlags.kind, "kind", "", "Filter by symbol kind (function, class, method, etc.)")
}
