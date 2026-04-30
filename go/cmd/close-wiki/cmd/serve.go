package cmd

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/server"
)

var serveFlags struct {
	port      int
	noBrowser bool
	model     string
}

var serveCmd = &cobra.Command{
	Use:   "serve [repo-path]",
	Short: "Start the close-wiki web UI",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}
		cfg := loadLLMConfig(serveFlags.model, "", "")
		addr := fmt.Sprintf(":%d", serveFlags.port)
		srv := server.New(root, outputDir, addr, cfg)
		return srv.Start(context.Background())
	},
}

func init() {
	serveCmd.Flags().IntVar(&serveFlags.port, "port", 7070, "HTTP port")
	serveCmd.Flags().BoolVar(&serveFlags.noBrowser, "no-browser", false, "Don't open browser")
	serveCmd.Flags().StringVar(&serveFlags.model, "model", "", "LLM model")
}
