package cmd

import (
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/rag"
)

var embedFlags struct {
	model     string
	provider  string
	apiKey    string
	baseURL   string
	outputDir string
	verbose   bool
}

var embedCmd = &cobra.Command{
	Use:   "embed [repo-path]",
	Short: "Build the RAG vector index for a repository",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}
		outDir := outputDir
		if embedFlags.outputDir != "" {
			outDir = embedFlags.outputDir
		}
		if err := os.MkdirAll(outDir, 0o755); err != nil {
			return err
		}
		color.New(color.FgCyan, color.Bold).Fprintf(os.Stderr, "close-wiki embed  ▸  %s\n", root)
		cfg := loadLLMConfig("", embedFlags.apiKey, embedFlags.baseURL)
		if embedFlags.model != "" {
			cfg.EmbedModel = embedFlags.model
		}
		if embedFlags.provider != "" {
			cfg.EmbedProvider = embedFlags.provider
		}
		progress := func(msg string) { fmt.Fprintln(os.Stderr, msg) }
		pipeline := rag.NewEmbedPipeline(outDir, cfg)
		n, err := pipeline.Build(root, progress)
		if err != nil {
			return err
		}
		color.New(color.FgGreen).Fprintf(os.Stderr, "✅ Embedded %d chunks\n", n)
		return nil
	},
}

func init() {
	embedCmd.Flags().StringVar(&embedFlags.model, "model", "", "Embedding model")
	embedCmd.Flags().StringVar(&embedFlags.provider, "provider", "", "Embedding provider")
	embedCmd.Flags().StringVar(&embedFlags.apiKey, "api-key", "", "API key override")
	embedCmd.Flags().StringVar(&embedFlags.baseURL, "base-url", "", "LLM base URL override")
	embedCmd.Flags().StringVar(&embedFlags.outputDir, "output-dir", "", "Output directory (default: .close-wiki)")
	embedCmd.Flags().BoolVarP(&embedFlags.verbose, "verbose", "v", false, "Verbose output")
}
