package cmd

import (
	"os"
	"path/filepath"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
	"github.com/unrealandychan/rekipedia/internal/config"
)

var noAgentFiles bool

var initCmd = &cobra.Command{
	Use:   "init [repo-path]",
	Short: "Initialise .rekipedia/ in a repository",
	Long:  `Creates .rekipedia/config.yml with defaults. Safe to re-run (idempotent).`,
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}

		// Check if already initialised before calling InitDir
		cfgPath := filepath.Join(root, ".rekipedia", "config.yml")
		_, statErr := os.Stat(cfgPath)
		alreadyExists := statErr == nil

		if err := config.InitDir(root); err != nil {
			return err
		}

		if alreadyExists {
			pterm.Warning.Println("Already initialised — skipping")
		} else {
			pterm.Success.Printfln("Initialised .rekipedia/ in %s", root)
			boxContent := ".rekipedia/config.yml  ✓\n.gitignore updated      ✓"
			pterm.DefaultBox.Println(boxContent)
			pterm.Info.Println("Next: run `rekipedia scan .`")
		}

		if !noAgentFiles {
			pterm.Info.Println("Writing agent instruction files…")
			results, err := config.WriteAgentFiles(root, false)
			if err != nil {
				return err
			}
			for _, r := range results {
				if r.Created {
					pterm.Success.Printfln("✔  Created %s (%s)", r.Path, r.Platform)
				} else {
					pterm.Warning.Printfln("⚠  %s already exists — skipping (%s)", r.Path, r.Platform)
				}
			}
		}

		return nil
	},
}

func init() {
	initCmd.Flags().BoolVar(&noAgentFiles, "no-agent-files", false, "Skip writing CLAUDE.md, AGENTS.md, and .github/copilot-instructions.md")
}

