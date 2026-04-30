package fsutil

import (
	"os"
	"path/filepath"
	"testing"
)

func TestIsImplementation(t *testing.T) {
	cases := []struct {
		path     string
		expected bool
	}{
		{"src/app.py", true},
		{"src/utils.py", true},
		{"tests/test_app.py", false},
		{"test_utils.py", false},
		{"spec/feature_spec.rb", false},
		{"__tests__/App.test.ts", false},
		{"src/testdata/fixture.json", false}, // "testdata" starts with "test"
		{"lib/config.py", true},
	}
	for _, tc := range cases {
		got := IsImplementation(tc.path)
		if got != tc.expected {
			t.Errorf("IsImplementation(%q) = %v, want %v", tc.path, got, tc.expected)
		}
	}
}

func TestDetectLanguage(t *testing.T) {
	lang, isCode, isDoc := DetectLanguage(".py")
	if lang != "python" || !isCode || isDoc {
		t.Errorf("expected python/true/false, got %s/%v/%v", lang, isCode, isDoc)
	}
	lang, isCode, isDoc = DetectLanguage(".md")
	if lang != "markdown" || isCode || !isDoc {
		t.Errorf("expected markdown/false/true, got %s/%v/%v", lang, isCode, isDoc)
	}
	lang, isCode, isDoc = DetectLanguage(".xyz")
	if lang != "" || isCode || isDoc {
		t.Errorf("expected empty/false/false for unknown ext")
	}
}

func TestWalkRepo(t *testing.T) {
	tmp := t.TempDir()
	// Create a small fake repo
	dirs := []string{"src", "tests", "node_modules"}
	for _, d := range dirs {
		_ = os.MkdirAll(filepath.Join(tmp, d), 0o755)
	}
	files := map[string]string{
		"src/app.py":              "def main(): pass",
		"src/utils.py":            "def helper(): pass",
		"tests/test_app.py":       "def test_main(): pass",
		"node_modules/lib.js":     "module.exports = {}",
		"README.md":               "# Hello",
		"binary.exe":              "\x00\x01\x02", // should be ignored (no known ext)
	}
	for path, content := range files {
		full := filepath.Join(tmp, path)
		_ = os.MkdirAll(filepath.Dir(full), 0o755)
		_ = os.WriteFile(full, []byte(content), 0o644)
	}

	found, err := WalkRepo(tmp, nil)
	if err != nil {
		t.Fatalf("WalkRepo error: %v", err)
	}

	paths := make(map[string]bool)
	for _, f := range found {
		paths[f.Path] = true
	}
	if !paths["src/app.py"] {
		t.Error("expected src/app.py in results")
	}
	if paths["node_modules/lib.js"] {
		t.Error("node_modules should be skipped")
	}
	if paths["binary.exe"] {
		t.Error("binary.exe should be skipped")
	}
}

func TestSHA256File(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "test.txt")
	_ = os.WriteFile(path, []byte("hello"), 0o644)
	hash, err := SHA256File(path)
	if err != nil {
		t.Fatalf("SHA256File error: %v", err)
	}
	// sha256("hello") = 2cf24dba...
	if len(hash) != 64 {
		t.Errorf("expected 64-char hex hash, got %d chars", len(hash))
	}
}

func TestSHA256FileDeterministic(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "f.txt")
	_ = os.WriteFile(path, []byte("content"), 0o644)
	h1, _ := SHA256File(path)
	h2, _ := SHA256File(path)
	if h1 != h2 {
		t.Error("SHA256 should be deterministic")
	}
}

func TestCategoriseFiles(t *testing.T) {
	files := []string{
		"src/app.py", "src/utils.py",
		"tests/test_app.py", "tests/test_utils.py",
		"config.yaml", "pyproject.toml",
	}
	c := CategoriseFiles(files)
	if c.Impl != 2 {
		t.Errorf("expected 2 impl files, got %d", c.Impl)
	}
	if c.Test != 2 {
		t.Errorf("expected 2 test files, got %d", c.Test)
	}
	if c.Config != 2 {
		t.Errorf("expected 2 config files, got %d", c.Config)
	}
	total := c.Impl + c.Test + c.Config
	if total != len(files) {
		t.Errorf("counts should sum to %d, got %d", len(files), total)
	}
}
