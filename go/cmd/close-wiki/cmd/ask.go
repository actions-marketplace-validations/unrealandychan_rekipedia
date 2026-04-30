package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var askFlags struct {
	repo  string
	model string
	query string
}

var askCmd = &cobra.Command{
	Use:   "ask",
	Short: "Ask a question about the scanned repository",
	Long: `Stream an answer from the LLM using wiki pages + RAG context.
Use -q for single-shot (non-interactive) mode.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Println("→ ask (not yet implemented)")
		return nil
	},
}

func init() {
	askCmd.Flags().StringVar(&askFlags.repo, "repo", ".", "Repo path")
	askCmd.Flags().StringVar(&askFlags.model, "model", "", "LLM model override")
	askCmd.Flags().StringVarP(&askFlags.query, "query", "q", "", "Single-shot question")
}
