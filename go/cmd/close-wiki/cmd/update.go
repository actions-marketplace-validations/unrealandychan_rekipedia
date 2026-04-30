package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/orchestrator"
)

var updateFlags struct {
	model     string
	verbose   bool
	languages string
	outputDir string
	noDocker  bool
}

var updateCmd = &cobra.Command{
	Use:   "update [repo-path]",
	Short: "Incremental update: re-scan changed files only",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}
		if err := os.MkdirAll(outputDir, 0o755); err != nil {
			return err
		}
		cfg := loadLLMConfig(updateFlags.model, "", "")
		progress := func(msg string) { fmt.Fprintln(os.Stderr, msg) }
		return orchestrator.RunUpdate(cmd.Context(), root, outputDir, orchestrator.UpdateOptions{
			LLMConfig: cfg,
			Progress:  progress,
			Languages: splitLanguages(updateFlags.languages),
		})
	},
}

func init() {
	updateCmd.Flags().StringVar(&updateFlags.model, "model", "", "LLM model override")
	updateCmd.Flags().BoolVarP(&updateFlags.verbose, "verbose", "v", false, "Verbose output")
	updateCmd.Flags().StringVarP(&updateFlags.languages, "languages", "l", "", "Comma-separated languages to include, e.g. python,typescript,go (default: all)")
	updateCmd.Flags().StringVar(&updateFlags.outputDir, "output-dir", "", "Output directory (default: .close-wiki)")
	updateCmd.Flags().BoolVar(&updateFlags.noDocker, "no-docker", false, "Skip Docker, run extractors in-process")
}
