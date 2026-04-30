package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var exportFlags struct {
	format string
	output string
}

var exportCmd = &cobra.Command{
	Use:   "export [repo-path]",
	Short: "Export wiki to markdown, zip, or JSON",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Printf("→ export as %s (not yet implemented)\n", exportFlags.format)
		return nil
	},
}

func init() {
	exportCmd.Flags().StringVar(&exportFlags.format, "format", "md", "Export format: md|zip|json")
	exportCmd.Flags().StringVarP(&exportFlags.output, "output", "o", "", "Output file/directory")
}
