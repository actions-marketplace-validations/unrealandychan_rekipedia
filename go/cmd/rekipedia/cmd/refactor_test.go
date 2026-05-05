package cmd

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

func TestRefactorCmdRegistered(t *testing.T) {
	found := false
	for _, c := range rootCmd.Commands() {
		if c.Name() == "refactor" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected 'refactor' to be registered as a subcommand")
	}
}

func TestRefactorCmdFlags(t *testing.T) {
	f := refactorCmd.Flags()
	for _, name := range []string{
		"no-llm", "stdout", "severity", "json",
		"model", "output-dir", "no-docker", "verbose", "languages",
	} {
		if f.Lookup(name) == nil {
			t.Errorf("refactor command missing flag --%s", name)
		}
	}
}

func TestRefactorCmdUseLine(t *testing.T) {
	if refactorCmd.Use == "" {
		t.Error("refactor command Use string must not be empty")
	}
}

// ---------------------------------------------------------------------------
// staticWalk
// ---------------------------------------------------------------------------

func makeTestRepo(t *testing.T, files map[string]string) string {
	t.Helper()
	dir := t.TempDir()
	for rel, content := range files {
		full := filepath.Join(dir, rel)
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatalf("mkdir: %v", err)
		}
		if err := os.WriteFile(full, []byte(content), 0o644); err != nil {
			t.Fatalf("write: %v", err)
		}
	}
	return dir
}

func TestStaticWalkFindsTODO(t *testing.T) {
	dir := makeTestRepo(t, map[string]string{
		"main.py": "x = 1\n# TODO: refactor this\ny = 2\n",
	})
	findings, err := staticWalk(dir)
	if err != nil {
		t.Fatalf("staticWalk: %v", err)
	}
	if len(findings) != 1 {
		t.Fatalf("expected 1 finding, got %d", len(findings))
	}
	if findings[0].Type != "TODO" {
		t.Errorf("expected TODO, got %q", findings[0].Type)
	}
	if findings[0].Severity != "medium" {
		t.Errorf("expected medium severity, got %q", findings[0].Severity)
	}
	if findings[0].Line != 2 {
		t.Errorf("expected line 2, got %d", findings[0].Line)
	}
}

func TestStaticWalkFindsFIXME(t *testing.T) {
	dir := makeTestRepo(t, map[string]string{
		"main.go": "// FIXME: broken logic\nfunc foo() {}\n",
	})
	findings, err := staticWalk(dir)
	if err != nil {
		t.Fatalf("staticWalk: %v", err)
	}
	if len(findings) != 1 {
		t.Fatalf("expected 1 finding, got %d", len(findings))
	}
	if findings[0].Type != "FIXME" {
		t.Errorf("expected FIXME, got %q", findings[0].Type)
	}
	if findings[0].Severity != "high" {
		t.Errorf("expected high severity, got %q", findings[0].Severity)
	}
}

func TestStaticWalkSkipsGitDir(t *testing.T) {
	dir := makeTestRepo(t, map[string]string{
		".git/COMMIT_EDITMSG": "# TODO: inside git\n",
		"src.py":              "# TODO: real one\n",
	})
	findings, err := staticWalk(dir)
	if err != nil {
		t.Fatalf("staticWalk: %v", err)
	}
	for _, f := range findings {
		if strings.HasPrefix(f.File, ".git") {
			t.Errorf("should not include .git findings, got %q", f.File)
		}
	}
	if len(findings) != 1 {
		t.Errorf("expected 1 finding, got %d", len(findings))
	}
}

func TestStaticWalkSkipsNodeModules(t *testing.T) {
	dir := makeTestRepo(t, map[string]string{
		"node_modules/lib.js": "// TODO: upstream fix\n",
		"src/app.js":          "// FIXME: our bug\n",
	})
	findings, err := staticWalk(dir)
	if err != nil {
		t.Fatalf("staticWalk: %v", err)
	}
	for _, f := range findings {
		if strings.HasPrefix(f.File, "node_modules") {
			t.Errorf("should not include node_modules findings, got %q", f.File)
		}
	}
}

func TestStaticWalkEmptyRepo(t *testing.T) {
	dir := t.TempDir()
	findings, err := staticWalk(dir)
	if err != nil {
		t.Fatalf("staticWalk: %v", err)
	}
	if len(findings) != 0 {
		t.Errorf("expected 0 findings, got %d", len(findings))
	}
}

// ---------------------------------------------------------------------------
// applyFilter
// ---------------------------------------------------------------------------

func TestApplyFilterAll(t *testing.T) {
	findings := []Finding{
		{Severity: "critical"},
		{Severity: "high"},
		{Severity: "medium"},
		{Severity: "low"},
	}
	got := applyFilter(findings, "all")
	if len(got) != 4 {
		t.Errorf("expected 4, got %d", len(got))
	}
	got = applyFilter(findings, "")
	if len(got) != 4 {
		t.Errorf("expected 4 for empty filter, got %d", len(got))
	}
}

func TestApplyFilterHigh(t *testing.T) {
	findings := []Finding{
		{Severity: "critical"},
		{Severity: "high"},
		{Severity: "medium"},
		{Severity: "low"},
	}
	got := applyFilter(findings, "high")
	if len(got) != 2 {
		t.Errorf("expected 2, got %d", len(got))
	}
	for _, f := range got {
		if f.Severity != "critical" && f.Severity != "high" {
			t.Errorf("unexpected severity %q after high filter", f.Severity)
		}
	}
}

func TestApplyFilterCritical(t *testing.T) {
	findings := []Finding{
		{Severity: "critical"},
		{Severity: "high"},
		{Severity: "low"},
	}
	got := applyFilter(findings, "critical")
	if len(got) != 1 || got[0].Severity != "critical" {
		t.Errorf("expected 1 critical finding, got %v", got)
	}
}

// ---------------------------------------------------------------------------
// buildStaticReport
// ---------------------------------------------------------------------------

func TestBuildStaticReportEmpty(t *testing.T) {
	report := buildStaticReport("/tmp/myrepo", nil)
	if !strings.Contains(report, "REFACTOR.md") {
		t.Error("expected REFACTOR.md header")
	}
	if !strings.Contains(report, "No static annotations") {
		t.Error("expected empty-findings message")
	}
}

func TestBuildStaticReportWithFindings(t *testing.T) {
	findings := []Finding{
		{Type: "FIXME", Severity: "high", File: "src/main.py", Line: 10, Description: "broken"},
		{Type: "TODO", Severity: "medium", File: "src/util.py", Line: 5, Description: "add test"},
	}
	report := buildStaticReport("/tmp/myrepo", findings)
	if !strings.Contains(report, "FIXME") {
		t.Error("expected FIXME in report")
	}
	if !strings.Contains(report, "broken") {
		t.Error("expected description in report")
	}
	if !strings.Contains(report, "TODO") {
		t.Error("expected TODO in report")
	}
}

// ---------------------------------------------------------------------------
// CLI — --no-llm writes REFACTOR.md
// ---------------------------------------------------------------------------

func TestRefactorNoLLMWritesFile(t *testing.T) {
	dir := makeTestRepo(t, map[string]string{
		"main.py": "# TODO: finish me\n",
	})
	outDir := t.TempDir()
	refactorFlags.noLLM = true
	refactorFlags.toStdout = false
	refactorFlags.severity = "all"
	refactorFlags.outputJSON = false
	refactorFlags.outputDir = outDir
	defer func() {
		refactorFlags.noLLM = false
		refactorFlags.toStdout = false
		refactorFlags.severity = "all"
		refactorFlags.outputJSON = false
		refactorFlags.outputDir = ""
	}()

	if err := refactorCmd.RunE(refactorCmd, []string{dir}); err != nil {
		t.Fatalf("refactorCmd.RunE: %v", err)
	}
	outPath := filepath.Join(outDir, "REFACTOR.md")
	if _, err := os.Stat(outPath); err != nil {
		t.Errorf("expected REFACTOR.md at %s: %v", outPath, err)
	}
	data, _ := os.ReadFile(outPath)
	if !strings.Contains(string(data), "TODO") {
		t.Error("expected TODO in REFACTOR.md")
	}
}

func TestRefactorJSONWritesFile(t *testing.T) {
	dir := makeTestRepo(t, map[string]string{
		"main.go": "// TODO: something\n",
	})
	outDir := t.TempDir()
	refactorFlags.noLLM = false
	refactorFlags.outputJSON = true
	refactorFlags.toStdout = false
	refactorFlags.severity = "all"
	refactorFlags.outputDir = outDir
	defer func() {
		refactorFlags.outputJSON = false
		refactorFlags.toStdout = false
		refactorFlags.severity = "all"
		refactorFlags.outputDir = ""
	}()

	if err := refactorCmd.RunE(refactorCmd, []string{dir}); err != nil {
		t.Fatalf("refactorCmd.RunE: %v", err)
	}
	outPath := filepath.Join(outDir, "REFACTOR.json")
	if _, err := os.Stat(outPath); err != nil {
		t.Errorf("expected REFACTOR.json at %s: %v", outPath, err)
	}
	raw, _ := os.ReadFile(outPath)
	var payload map[string]interface{}
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatalf("unmarshal REFACTOR.json: %v", err)
	}
	if _, ok := payload["findings"]; !ok {
		t.Error("expected 'findings' key in REFACTOR.json")
	}
}

// ---------------------------------------------------------------------------
// scan --with-refactor flag
// ---------------------------------------------------------------------------

func TestScanHasWithRefactorFlag(t *testing.T) {
	f := scanCmd.Flags().Lookup("with-refactor")
	if f == nil {
		t.Error("scan command missing --with-refactor flag")
	}
}
