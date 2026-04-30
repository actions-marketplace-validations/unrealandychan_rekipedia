package exporter

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// MarkdownExporter writes wiki markdown pages and diagram files.
type MarkdownExporter struct {
	outputDir string
}

// NewMarkdownExporter creates a MarkdownExporter.
func NewMarkdownExporter(outputDir string) *MarkdownExporter {
	return &MarkdownExporter{outputDir: outputDir}
}

// Export writes wiki/{slug}.md and diagrams/{name}.md.
// Skips wiki pages that already exist with "pin: true" in their frontmatter.
func (e *MarkdownExporter) Export(
	pages map[string]string,
	pageTitles map[string]string,
	diagrams map[string][2]string,
) error {
	wikiDir := filepath.Join(e.outputDir, "wiki")
	if err := os.MkdirAll(wikiDir, 0o755); err != nil {
		return err
	}

	for slug, content := range pages {
		dest := filepath.Join(wikiDir, slug+".md")
		// Check for pin: true in existing file
		if existing, err := os.ReadFile(dest); err == nil {
			if isPinned(string(existing)) {
				continue
			}
		}
		if err := os.WriteFile(dest, []byte(content), 0o644); err != nil {
			return fmt.Errorf("write wiki/%s.md: %w", slug, err)
		}
	}

	// Write diagrams
	if len(diagrams) > 0 {
		diagDir := filepath.Join(e.outputDir, "diagrams")
		if err := os.MkdirAll(diagDir, 0o755); err != nil {
			return err
		}
		for name, pair := range diagrams {
			title := pair[0]
			mermaid := pair[1]
			content := fmt.Sprintf("# %s\n\n```mermaid\n%s\n```\n", title, mermaid)
			dest := filepath.Join(diagDir, name+".md")
			if err := os.WriteFile(dest, []byte(content), 0o644); err != nil {
				return fmt.Errorf("write diagrams/%s.md: %w", name, err)
			}
		}
	}

	return nil
}

// isPinned returns true if the frontmatter contains "pin: true".
func isPinned(content string) bool {
	if !strings.HasPrefix(content, "---") {
		return false
	}
	end := strings.Index(content[3:], "---")
	if end < 0 {
		return false
	}
	frontmatter := content[3 : end+3]
	for _, line := range strings.Split(frontmatter, "\n") {
		line = strings.TrimSpace(line)
		if line == "pin: true" {
			return true
		}
	}
	return false
}
