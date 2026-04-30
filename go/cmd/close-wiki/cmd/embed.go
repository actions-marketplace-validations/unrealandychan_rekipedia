package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var embedFlags struct {
	model    string
	provider string
}

var embedCmd = &cobra.Command{
	Use:   "embed [repo-path]",
	Short: "Build the RAG vector index for a repository",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Println("→ embed (not yet implemented)")
		return nil
	},
}

func init() {
	embedCmd.Flags().StringVar(&embedFlags.model, "model", "", "Embedding model")
	embedCmd.Flags().StringVar(&embedFlags.provider, "provider", "", "Embedding provider")
}
