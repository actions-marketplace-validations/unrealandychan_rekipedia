package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/unrealandychan/rekipedia/internal/storage"
)

var impactFlags struct {
	outputDir string
	depth     int
}

var impactCmd = &cobra.Command{
	Use:   "impact <file>",
	Short: "Show blast-radius for a changed file (BFS over reverse call graph)",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		targetFile := args[0]
		dbPath := storage.DefaultPath(impactFlags.outputDir)
		store, err := storage.Open(dbPath)
		if err != nil {
			return fmt.Errorf("open store: %w", err)
		}
		defer store.Close()

		runID, err := store.LatestRunID(impactFlags.outputDir)
		if err != nil || runID == "" {
			return fmt.Errorf("no scan found in %s — run reki scan first", impactFlags.outputDir)
		}

		symbols, err := store.ListSymbols(runID)
		if err != nil {
			return err
		}
		rels, err := store.ListRelationships(runID)
		if err != nil {
			return err
		}

		symFile := make(map[string]string)
		fileSyms := make(map[string][]string)
		for _, s := range symbols {
			symFile[s.Name] = s.File
			fileSyms[s.File] = append(fileSyms[s.File], s.Name)
		}

		reverse := make(map[string][]string)
		for _, r := range rels {
			if string(r.Kind) == "calls" {
				reverse[r.To] = append(reverse[r.To], r.From)
			}
		}

		seeds := fileSyms[targetFile]
		visited := make(map[string]bool)
		for _, s := range seeds {
			visited[s] = true
		}
		type qitem struct {
			sym   string
			depth int
		}
		queue := make([]qitem, 0)
		for _, s := range seeds {
			queue = append(queue, qitem{s, 0})
		}

		maxDepth := impactFlags.depth
		for len(queue) > 0 {
			cur := queue[0]
			queue = queue[1:]
			if cur.depth >= maxDepth {
				continue
			}
			for _, caller := range reverse[cur.sym] {
				if !visited[caller] {
					visited[caller] = true
					queue = append(queue, qitem{caller, cur.depth + 1})
				}
			}
		}

		seedSet := make(map[string]bool)
		for _, s := range seeds {
			seedSet[s] = true
		}

		affectedFiles := make(map[string]bool)
		var affectedSyms []string
		for sym := range visited {
			if seedSet[sym] {
				continue
			}
			affectedSyms = append(affectedSyms, sym)
			if f, ok := symFile[sym]; ok {
				affectedFiles[f] = true
			}
		}

		fmt.Printf("Impact: %s (depth=%d)\n", targetFile, maxDepth)
		fmt.Printf("Seed symbols: %d\n", len(seeds))
		fmt.Printf("Affected symbols: %d\n", len(affectedSyms))
		fmt.Printf("Affected files: %d\n", len(affectedFiles))

		var testFiles []string
		for f := range affectedFiles {
			if strings.Contains(f, "test") {
				testFiles = append(testFiles, f)
			}
		}
		if len(testFiles) > 0 {
			fmt.Printf("Related tests: %s\n", strings.Join(testFiles, ", "))
		}
		for f := range affectedFiles {
			fmt.Printf("  -> %s\n", f)
		}
		return nil
	},
}

func init() {
	impactCmd.Flags().StringVar(&impactFlags.outputDir, "output-dir", ".", "Directory with .rekipedia/")
	impactCmd.Flags().IntVar(&impactFlags.depth, "depth", 2, "BFS traversal depth")
}
