package cmd

import (
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/orchestrator"
)

var askFlags struct {
	repo      string
	model     string
	query     string
	stream    bool
	outputDir string
}

var askCmd = &cobra.Command{
	Use:   "ask",
	Short: "Ask a question about the scanned repository",
	Long: `Stream an answer from the LLM using wiki pages + RAG context.
Use -q for single-shot (non-interactive) mode.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		question := askFlags.query
		if question == "" {
			if len(args) > 0 {
				question = args[0]
			} else {
				return fmt.Errorf("provide a question via -q or as an argument")
			}
		}

		color.New(color.FgCyan, color.Bold).Fprintf(os.Stderr, "close-wiki ask  ▸  %s\n", askFlags.repo)

		cfg := loadLLMConfig(askFlags.model, "", "")
		opts := orchestrator.AskOptions{LLMConfig: cfg}

		outDir := askFlags.outputDir
		if outDir == "" {
			outDir = ".close-wiki"
		}

		if askFlags.stream {
			return orchestrator.StreamAsk(cmd.Context(), question, askFlags.repo, outDir, opts, func(chunk string) {
				fmt.Print(chunk)
			})
		}

		result, err := orchestrator.RunAsk(cmd.Context(), question, askFlags.repo, outDir, opts)
		if err != nil {
			return err
		}
		fmt.Println(result.Answer)
		return nil
	},
}

func init() {
	askCmd.Flags().StringVar(&askFlags.repo, "repo", ".", "Repo path")
	askCmd.Flags().StringVar(&askFlags.outputDir, "output-dir", "", "Output directory (default: .close-wiki)")
	askCmd.Flags().StringVar(&askFlags.model, "model", "", "LLM model override")
	askCmd.Flags().StringVarP(&askFlags.query, "query", "q", "", "Single-shot question")
	askCmd.Flags().BoolVar(&askFlags.stream, "stream", false, "Stream the response")
}

var _ = os.Stderr // keep os imported for potential use
