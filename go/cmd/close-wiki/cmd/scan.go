package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var scanFlags struct {
	model         string
	apiKey        string
	baseURL       string
	outputDir     string
	verbose       bool
	embedModel    string
	embedProvider string
}

var scanCmd = &cobra.Command{
	Use:   "scan [repo-path]",
	Short: "Full scan: extract, plan, and generate wiki pages",
	Long: `Performs a full scan of the repository:
  1. Walk files and extract symbols/relationships
  2. Run PlannerAgent to design wiki structure
  3. Build wiki pages concurrently via LLM
  4. Save results to .close-wiki/store.db and .close-wiki/wiki/`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}
		// TODO: wire orchestrator.RunDigest
		fmt.Printf("→ Scanning %s (not yet implemented — use Python CLI for now)\n", root)
		return nil
	},
}

func init() {
	scanCmd.Flags().StringVar(&scanFlags.model, "model", "", "LLM model override")
	scanCmd.Flags().StringVar(&scanFlags.apiKey, "api-key", "", "API key override")
	scanCmd.Flags().StringVar(&scanFlags.baseURL, "base-url", "", "LLM base URL override")
	scanCmd.Flags().StringVar(&scanFlags.outputDir, "output-dir", "", "Output directory (default: .close-wiki)")
	scanCmd.Flags().BoolVarP(&scanFlags.verbose, "verbose", "v", false, "Verbose output")
	scanCmd.Flags().StringVar(&scanFlags.embedModel, "embed-model", "", "Embedding model")
	scanCmd.Flags().StringVar(&scanFlags.embedProvider, "embed-provider", "", "Embedding provider")
}
