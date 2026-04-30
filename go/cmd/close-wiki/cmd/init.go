package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/unrealandychan/close-wiki/internal/config"
)

var initCmd = &cobra.Command{
	Use:   "init [repo-path]",
	Short: "Initialise .close-wiki/ in a repository",
	Long:  `Creates .close-wiki/config.yml with defaults. Safe to re-run (idempotent).`,
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}
		if err := config.InitDir(root); err != nil {
			return fmt.Errorf("init failed: %w", err)
		}
		fmt.Printf("✓ Initialised .close-wiki/ in %s\n", root)
		return nil
	},
}
