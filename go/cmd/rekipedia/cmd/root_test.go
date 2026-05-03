package cmd

import (
	"os"
	"strings"
	"testing"
)

func TestRootVersionFlag(t *testing.T) {
	v := rootCmd.Version
	if v == "" {
		t.Error("expected non-empty rootCmd.Version")
	}
	if !strings.Contains(v, "dev") && !strings.Contains(v, "commit") {
		t.Errorf("version string unexpected: %q", v)
	}
}

func TestRootCommandHasSubcommands(t *testing.T) {
	names := map[string]bool{}
	for _, c := range rootCmd.Commands() {
		names[c.Name()] = true
	}
	for _, want := range []string{"scan", "serve", "hook", "init", "ask", "export"} {
		if !names[want] {
			t.Errorf("expected subcommand %q to be registered", want)
		}
	}
}

func TestHookInstallIdempotent(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir

	if err := hookInstallCmd.RunE(hookInstallCmd, nil); err != nil {
		t.Fatalf("first install: %v", err)
	}
	if err := hookInstallCmd.RunE(hookInstallCmd, nil); err != nil {
		t.Fatalf("second install: %v", err)
	}
}

func TestHookUninstallMissing(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir

	if err := hookUninstallCmd.RunE(hookUninstallCmd, nil); err != nil {
		t.Fatalf("uninstall with no hook: %v", err)
	}
}

func TestHookStatusNotOurs(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir

	// Write a hook not made by rekipedia
	hookPath := dir + "/.git/hooks/post-commit"
	if err := os.WriteFile(hookPath, []byte("#!/bin/sh\necho custom\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := hookStatusCmd.RunE(hookStatusCmd, nil); err != nil {
		t.Fatalf("status with non-rekipedia hook: %v", err)
	}
}

func TestSplitLanguages(t *testing.T) {
	cases := []struct {
		input string
		want  []string
	}{
		{"", nil},
		{"go", []string{"go"}},
		{"go,python", []string{"go", "python"}},
		{"Go, Python , ", []string{"go", "python"}},
		{"  ", nil},
	}
	for _, c := range cases {
		got := splitLanguages(c.input)
		if len(got) != len(c.want) {
			t.Errorf("splitLanguages(%q) = %v, want %v", c.input, got, c.want)
			continue
		}
		for i := range got {
			if got[i] != c.want[i] {
				t.Errorf("splitLanguages(%q)[%d] = %q, want %q", c.input, i, got[i], c.want[i])
			}
		}
	}
}

func TestLoadLLMConfig(t *testing.T) {
	cfg := loadLLMConfig("my-model", "my-key", "http://localhost")
	if cfg.Model != "my-model" {
		t.Errorf("expected model my-model, got %q", cfg.Model)
	}
	if cfg.APIKey != "my-key" {
		t.Errorf("expected key my-key, got %q", cfg.APIKey)
	}
	if cfg.BaseURL != "http://localhost" {
		t.Errorf("expected baseURL, got %q", cfg.BaseURL)
	}
}

func TestLoadLLMConfigDefaults(t *testing.T) {
	cfg := loadLLMConfig("", "", "")
	// Should have some default model
	if cfg.Model == "" {
		t.Error("expected non-empty default model")
	}
}
