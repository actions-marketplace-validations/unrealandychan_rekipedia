package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
)

var diffFlags struct {
	repo     string
	fromRef  string
	toRef    string
	outputDr string
	format   string
}

var diffCmd = &cobra.Command{
	Use:   "diff",
	Short: "Show a commit-level knowledge diff between two refs",
	RunE: func(cmd *cobra.Command, args []string) error {
		repoPath := diffFlags.repo
		if repoPath == "" {
			repoPath = "."
		}
		rekiDir := diffFlags.outputDr
		if rekiDir == "" {
			abs, err := filepath.Abs(repoPath)
			if err != nil {
				return err
			}
			rekiDir = filepath.Join(abs, ".rekipedia")
		}

		fromRef := diffFlags.fromRef
		toRef := diffFlags.toRef
		format := diffFlags.format

		// Get changed files
		changedFiles := []string{}
		out, err := runGit(repoPath, "diff", "--name-only", fromRef, toRef)
		if err == nil && out != "" {
			for _, line := range strings.Split(out, "\n") {
				if strings.TrimSpace(line) != "" {
					changedFiles = append(changedFiles, line)
				}
			}
		}

		// Load current symbols
		symbolsPath := filepath.Join(rekiDir, "exports", "symbols.json")
		currentSymbols, _ := loadSymbolsJSON(symbolsPath)

		// Try previous symbols
		prevRaw, err := runGit(repoPath, "show", fromRef+":.rekipedia/exports/symbols.json")
		prevSymbols := []map[string]interface{}{}
		if err == nil && prevRaw != "" {
			_ = json.Unmarshal([]byte(prevRaw), &prevSymbols)
		}

		added := []string{}
		removed := []string{}
		changed := []string{}

		if len(prevSymbols) == 0 {
			for _, s := range currentSymbols {
				added = append(added, symbolKey(s))
			}
		} else {
			prevMap := map[string]bool{}
			currMap := map[string]bool{}
			for _, s := range prevSymbols {
				prevMap[symbolKey(s)] = true
			}
			for _, s := range currentSymbols {
				k := symbolKey(s)
				currMap[k] = true
				if !prevMap[k] {
					added = append(added, k)
				} else if isInChangedFiles(s, changedFiles) {
					changed = append(changed, k)
				}
			}
			for _, s := range prevSymbols {
				k := symbolKey(s)
				if !currMap[k] {
					removed = append(removed, k)
				}
			}
		}

		content := ""
		if format == "text" {
			content = formatDiffText(added, removed, changed, changedFiles, fromRef, toRef)
		} else {
			content = formatDiffMd(added, removed, changed, changedFiles, fromRef, toRef)
		}

		fmt.Print(content)

		// Write to file
		ext := "md"
		if format == "text" {
			ext = "txt"
		}
		_ = os.MkdirAll(rekiDir, 0o755)
		outFile := filepath.Join(rekiDir, "diff."+ext)
		_ = os.WriteFile(outFile, []byte(content), 0o644)
		fmt.Fprintf(os.Stderr, "\n[diff written to %s]\n", outFile)

		return nil
	},
}

func runGit(dir string, args ...string) (string, error) {
	c := exec.Command("git", args...)
	c.Dir = dir
	out, err := c.Output()
	return strings.TrimSpace(string(out)), err
}

func loadSymbolsJSON(path string) ([]map[string]interface{}, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var list []map[string]interface{}
	if err := json.Unmarshal(data, &list); err != nil {
		// Try wrapped format
		var wrapped map[string]interface{}
		if err2 := json.Unmarshal(data, &wrapped); err2 != nil {
			return nil, err
		}
		if syms, ok := wrapped["symbols"].([]interface{}); ok {
			for _, s := range syms {
				if m, ok := s.(map[string]interface{}); ok {
					list = append(list, m)
				}
			}
		}
	}
	return list, nil
}

func symbolKey(s map[string]interface{}) string {
	if v, ok := s["name"].(string); ok && v != "" {
		return v
	}
	if v, ok := s["qualified_name"].(string); ok && v != "" {
		return v
	}
	return fmt.Sprintf("%v", s["id"])
}

func isInChangedFiles(s map[string]interface{}, changedFiles []string) bool {
	symFile, _ := s["file"].(string)
	if symFile == "" {
		symFile, _ = s["source_file"].(string)
	}
	if symFile == "" {
		return false
	}
	for _, cf := range changedFiles {
		if strings.HasSuffix(symFile, cf) || strings.HasSuffix(cf, symFile) {
			return true
		}
	}
	return false
}

func formatDiffMd(added, removed, changed, changedFiles []string, fromRef, toRef string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# Knowledge Diff: `%s` → `%s`\n\n", fromRef, toRef)

	if len(changedFiles) > 0 {
		b.WriteString("## Changed Files\n\n")
		for _, f := range changedFiles {
			fmt.Fprintf(&b, "- `%s`\n", f)
		}
		b.WriteString("\n")
	}

	if len(added) == 0 && len(removed) == 0 && len(changed) == 0 {
		b.WriteString("## No Changes\n\n_No symbol or relationship changes detected._\n\n")
		return b.String()
	}

	if len(added) > 0 {
		b.WriteString("## Added Symbols\n\n")
		for _, s := range added {
			fmt.Fprintf(&b, "+ `%s`\n", s)
		}
		b.WriteString("\n")
	}
	if len(removed) > 0 {
		b.WriteString("## Removed Symbols\n\n")
		for _, s := range removed {
			fmt.Fprintf(&b, "- `%s`\n", s)
		}
		b.WriteString("\n")
	}
	if len(changed) > 0 {
		b.WriteString("## Changed Symbols\n\n")
		for _, s := range changed {
			fmt.Fprintf(&b, "~ `%s`\n", s)
		}
		b.WriteString("\n")
	}
	return b.String()
}

func formatDiffText(added, removed, changed, changedFiles []string, fromRef, toRef string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Knowledge Diff: %s -> %s\n", fromRef, toRef)
	b.WriteString(strings.Repeat("=", 40) + "\n")

	if len(changedFiles) > 0 {
		b.WriteString("\nChanged Files:\n")
		for _, f := range changedFiles {
			fmt.Fprintf(&b, "  %s\n", f)
		}
	}

	if len(added) == 0 && len(removed) == 0 && len(changed) == 0 {
		b.WriteString("\nNo changes detected.\n")
		return b.String()
	}

	if len(added) > 0 {
		b.WriteString("\nAdded Symbols:\n")
		for _, s := range added {
			fmt.Fprintf(&b, "  + %s\n", s)
		}
	}
	if len(removed) > 0 {
		b.WriteString("\nRemoved Symbols:\n")
		for _, s := range removed {
			fmt.Fprintf(&b, "  - %s\n", s)
		}
	}
	if len(changed) > 0 {
		b.WriteString("\nChanged Symbols:\n")
		for _, s := range changed {
			fmt.Fprintf(&b, "  ~ %s\n", s)
		}
	}
	return b.String()
}

func init() {
	diffCmd.Flags().StringVar(&diffFlags.repo, "repo", ".", "Path to the git repository")
	diffCmd.Flags().StringVar(&diffFlags.fromRef, "from-ref", "HEAD~1", "Starting git ref")
	diffCmd.Flags().StringVar(&diffFlags.toRef, "to-ref", "HEAD", "Ending git ref")
	diffCmd.Flags().StringVar(&diffFlags.outputDr, "output-dir", "", "Directory to write diff output")
	diffCmd.Flags().StringVar(&diffFlags.format, "format", "md", "Output format (md|text)")
}
