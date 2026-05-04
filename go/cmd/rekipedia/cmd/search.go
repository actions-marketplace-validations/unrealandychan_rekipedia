package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/unrealandychan/rekipedia/internal/storage"
)

var searchFlags struct {
	outputDir string
}

var searchCmd = &cobra.Command{
	Use:   "search <query>",
	Short: "Search symbols in the codebase graph",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		query := strings.ToLower(args[0])
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
			score int
		}
		var results []result
		for _, s := range symbols {
			nl := strings.ToLower(s.Name)
			score := 0
			if nl == query {
				score = 3
			} else if strings.HasPrefix(nl, query) {
				score = 2
			} else if strings.Contains(nl, query) {
				score = 1
			}
			if score > 0 {
				results = append(results, result{s.Name, string(s.Kind), s.File, score})
			}
		}

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
}
