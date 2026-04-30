package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var updateFlags struct {
	model   string
	verbose bool
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
		fmt.Printf("→ Updating %s (not yet implemented)\n", root)
		return nil
	},
}

func init() {
	updateCmd.Flags().StringVar(&updateFlags.model, "model", "", "LLM model override")
	updateCmd.Flags().BoolVarP(&updateFlags.verbose, "verbose", "v", false, "Verbose output")
}
