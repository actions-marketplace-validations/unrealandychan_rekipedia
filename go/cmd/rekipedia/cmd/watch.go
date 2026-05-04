package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

var watchConfigPath = filepath.Join(os.Getenv("HOME"), ".rekipedia", "watch.json")

type watchConfig struct {
	Repos []string `json:"repos"`
}

func loadWatchConfig() watchConfig {
	data, err := os.ReadFile(watchConfigPath)
	if err != nil {
		return watchConfig{}
	}
	var cfg watchConfig
	_ = json.Unmarshal(data, &cfg)
	return cfg
}

func saveWatchConfig(cfg watchConfig) error {
	_ = os.MkdirAll(filepath.Dir(watchConfigPath), 0o755)
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(watchConfigPath, data, 0o644)
}

var watchCmd = &cobra.Command{
	Use:   "watch",
	Short: "Multi-repo daemon — watch directories and auto-index on change",
}

var watchAddCmd = &cobra.Command{
	Use:   "add <path>",
	Short: "Register a repo to watch",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		abs, err := filepath.Abs(args[0])
		if err != nil {
			return err
		}
		cfg := loadWatchConfig()
		for _, r := range cfg.Repos {
			if r == abs {
				fmt.Printf("Already registered: %s\n", abs)
				return nil
			}
		}
		cfg.Repos = append(cfg.Repos, abs)
		if err := saveWatchConfig(cfg); err != nil {
			return err
		}
		fmt.Printf("Added repo: %s\n", abs)
		return nil
	},
}

var watchRemoveCmd = &cobra.Command{
	Use:   "remove <path>",
	Short: "Unregister a repo",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		abs, _ := filepath.Abs(args[0])
		cfg := loadWatchConfig()
		newRepos := cfg.Repos[:0]
		for _, r := range cfg.Repos {
			if r != abs {
				newRepos = append(newRepos, r)
			}
		}
		cfg.Repos = newRepos
		_ = saveWatchConfig(cfg)
		fmt.Printf("Removed: %s\n", abs)
		return nil
	},
}

var watchListCmd = &cobra.Command{
	Use:   "list",
	Short: "List registered repos",
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := loadWatchConfig()
		if len(cfg.Repos) == 0 {
			fmt.Println("No repos registered. Use: reki watch add <path>")
			return nil
		}
		for _, r := range cfg.Repos {
			fmt.Println(r)
		}
		return nil
	},
}

var watchStartCmd = &cobra.Command{
	Use:   "start",
	Short: "Start watching (Go daemon stub — full implementation pending)",
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := loadWatchConfig()
		if len(cfg.Repos) == 0 {
			fmt.Println("No repos registered. Use: reki watch add <path>")
			return nil
		}
		fmt.Println("Watch daemon not yet fully implemented in Go. Use Python: reki watch start")
		fmt.Println("Registered repos:")
		for _, r := range cfg.Repos {
			fmt.Printf("  %s\n", r)
		}
		return nil
	},
}

func init() {
	watchCmd.AddCommand(watchAddCmd, watchRemoveCmd, watchListCmd, watchStartCmd)
}
