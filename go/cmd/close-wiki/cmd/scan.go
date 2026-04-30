package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/config"
	"github.com/unrealandychan/close-wiki/internal/models"
	"github.com/unrealandychan/close-wiki/internal/orchestrator"
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

		outDir := outputDir
		if scanFlags.outputDir != "" {
			outDir = scanFlags.outputDir
		}
		if err := os.MkdirAll(outDir, 0o755); err != nil {
			return err
		}

		cfg := loadLLMConfig(scanFlags.model, scanFlags.apiKey, scanFlags.baseURL)

		progress := func(msg string) {
			fmt.Fprintln(os.Stderr, msg)
		}

		return orchestrator.RunDigest(cmd.Context(), root, outDir, orchestrator.DigestOptions{
			LLMConfig: cfg,
			Verbose:   scanFlags.verbose,
			Progress:  progress,
		})
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

// loadLLMConfig merges flags with config file defaults.
func loadLLMConfig(model, apiKey, baseURL string) models.LLMConfig {
	cfg, err := config.Load("")
	var llmCfg models.LLMConfig
	if err == nil {
		llmCfg = cfg.LLM
	} else {
		llmCfg = models.DefaultLLMConfig()
	}
	if model != "" {
		llmCfg.Model = model
	}
	if apiKey != "" {
		llmCfg.APIKey = apiKey
	}
	if baseURL != "" {
		llmCfg.BaseURL = baseURL
	}
	return llmCfg
}
