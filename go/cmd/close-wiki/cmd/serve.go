package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var serveFlags struct {
	port      int
	noBrowser bool
}

var serveCmd = &cobra.Command{
	Use:   "serve [repo-path]",
	Short: "Start the close-wiki web UI",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Printf("→ serve on :%d (not yet implemented)\n", serveFlags.port)
		return nil
	},
}

func init() {
	serveCmd.Flags().IntVar(&serveFlags.port, "port", 7070, "HTTP port")
	serveCmd.Flags().BoolVar(&serveFlags.noBrowser, "no-browser", false, "Don't open browser")
}
