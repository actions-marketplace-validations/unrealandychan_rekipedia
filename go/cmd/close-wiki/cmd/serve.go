package cmd

import (
	"context"
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/unrealandychan/close-wiki/internal/server"
)

var serveFlags struct {
	port      int
	noBrowser bool
	model     string
	host      string
	outputDir string
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
		color.New(color.FgCyan, color.Bold).Fprintf(os.Stderr, "close-wiki serve  ▸  %s\n", root)
		cfg := loadLLMConfig(serveFlags.model, "", "")
		host := serveFlags.host
		if host == "" {
			host = "127.0.0.1"
		}
		addr := fmt.Sprintf("%s:%d", host, serveFlags.port)
		outDir := serveFlags.outputDir
		if outDir == "" {
			outDir = ".close-wiki"
		}
		srv := server.New(root, outDir, addr, cfg)
		return srv.Start(context.Background())
	},
}

func init() {
	serveCmd.Flags().IntVar(&serveFlags.port, "port", 7070, "HTTP port")
	serveCmd.Flags().StringVar(&serveFlags.host, "host", "", "Bind host (default: 127.0.0.1)")
	serveCmd.Flags().StringVar(&serveFlags.outputDir, "output-dir", "", "Output directory (default: .close-wiki)")
	serveCmd.Flags().BoolVar(&serveFlags.noBrowser, "no-browser", false, "Don't open browser")
	serveCmd.Flags().StringVar(&serveFlags.model, "model", "", "LLM model")
}
