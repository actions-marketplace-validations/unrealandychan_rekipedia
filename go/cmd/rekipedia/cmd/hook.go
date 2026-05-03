package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
)

const rekipediaHookMarker = "# rekipedia post-commit hook"
const rekipediaHookContent = "#!/bin/sh\n# rekipedia post-commit hook\nrekipedia update 2>&1 | tail -5\n"

var hookRepo string

var hookCmd = &cobra.Command{
	Use:   "hook",
	Short: "Manage rekipedia git hooks.",
}

var hookInstallCmd = &cobra.Command{
	Use:   "install",
	Short: "Install post-commit hook.",
	RunE: func(cmd *cobra.Command, args []string) error {
		hookPath := filepath.Join(hookRepo, ".git", "hooks", "post-commit")
		if err := os.MkdirAll(filepath.Dir(hookPath), 0o755); err != nil {
			return fmt.Errorf("create hooks dir: %w", err)
		}
		if err := os.WriteFile(hookPath, []byte(rekipediaHookContent), 0o755); err != nil {
			return fmt.Errorf("write hook: %w", err)
		}
		fmt.Println("✓ post-commit hook installed")
		return nil
	},
}

var hookUninstallCmd = &cobra.Command{
	Use:   "uninstall",
	Short: "Uninstall post-commit hook.",
	RunE: func(cmd *cobra.Command, args []string) error {
		hookPath := filepath.Join(hookRepo, ".git", "hooks", "post-commit")
		data, err := os.ReadFile(hookPath)
		if err != nil {
			fmt.Println("⚠ hook file not found — nothing to uninstall")
			return nil
		}
		if !strings.Contains(string(data), rekipediaHookMarker) {
			fmt.Println("⚠ hook file exists but was not installed by rekipedia — leaving it untouched")
			return nil
		}
		if err := os.Remove(hookPath); err != nil {
			return fmt.Errorf("remove hook: %w", err)
		}
		fmt.Println("✓ post-commit hook removed")
		return nil
	},
}

var hookStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show post-commit hook status.",
	RunE: func(cmd *cobra.Command, args []string) error {
		hookPath := filepath.Join(hookRepo, ".git", "hooks", "post-commit")
		data, err := os.ReadFile(hookPath)
		if err != nil {
			fmt.Println("not installed")
			return nil
		}
		if strings.Contains(string(data), rekipediaHookMarker) {
			fmt.Println("installed")
		} else {
			fmt.Println("not installed (hook exists but was not created by rekipedia)")
		}
		return nil
	},
}

func init() {
	hookCmd.PersistentFlags().StringVar(&hookRepo, "repo", ".", "Path to git repository root")
	hookCmd.AddCommand(hookInstallCmd, hookUninstallCmd, hookStatusCmd)
}
