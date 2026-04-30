package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/rag"
)

var embedFlags struct {
	model     string
	provider  string
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
		if err := os.MkdirAll(outputDir, 0o755); err != nil {
			return err
		}
		cfg := loadLLMConfig("", "", "")
		if embedFlags.model != "" {
			cfg.EmbedModel = embedFlags.model
		}
		if embedFlags.provider != "" {
			cfg.EmbedProvider = embedFlags.provider
		}
		progress := func(msg string) { fmt.Fprintln(os.Stderr, msg) }
		pipeline := rag.NewEmbedPipeline(outputDir, cfg)
		n, err := pipeline.Build(root, progress)
		if err != nil {
			return err
		}
		fmt.Fprintf(os.Stderr, "Embedded %d chunks\n", n)
		return nil
	},
}

func init() {
	embedCmd.Flags().StringVar(&embedFlags.model, "model", "", "Embedding model")
	embedCmd.Flags().StringVar(&embedFlags.provider, "provider", "", "Embedding provider")
	embedCmd.Flags().StringVar(&embedFlags.outputDir, "output-dir", "", "Output directory (default: .close-wiki)")
	embedCmd.Flags().BoolVarP(&embedFlags.verbose, "verbose", "v", false, "Verbose output")
}
