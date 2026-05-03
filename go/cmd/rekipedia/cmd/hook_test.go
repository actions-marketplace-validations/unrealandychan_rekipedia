package cmd

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func makeGitDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	hooksDir := filepath.Join(dir, ".git", "hooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		t.Fatal(err)
	}
	return dir
}

func TestHookInstall(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir

	if err := hookInstallCmd.RunE(hookInstallCmd, nil); err != nil {
		t.Fatalf("install failed: %v", err)
	}

	hookPath := filepath.Join(dir, ".git", "hooks", "post-commit")
	data, err := os.ReadFile(hookPath)
	if err != nil {
		t.Fatalf("hook file not found: %v", err)
	}

	content := string(data)
	if !strings.Contains(content, rekipediaHookMarker) {
		t.Errorf("hook missing marker, got: %s", content)
	}
	if !strings.Contains(content, "rekipedia update") {
		t.Errorf("hook missing 'rekipedia update', got: %s", content)
	}

	info, err := os.Stat(hookPath)
	if err != nil {
		t.Fatal(err)
	}
	perm := info.Mode().Perm()
	if perm&0o111 == 0 {
		t.Errorf("hook is not executable, mode: %v", perm)
	}
}

func TestHookUninstall(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir
	hookPath := filepath.Join(dir, ".git", "hooks", "post-commit")

	// Install first
	if err := os.WriteFile(hookPath, []byte(rekipediaHookContent), 0o755); err != nil {
		t.Fatal(err)
	}

	if err := hookUninstallCmd.RunE(hookUninstallCmd, nil); err != nil {
		t.Fatalf("uninstall failed: %v", err)
	}

	if _, err := os.Stat(hookPath); !os.IsNotExist(err) {
		t.Error("expected hook file to be removed")
	}
}

func TestHookUninstallNotOurs(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir
	hookPath := filepath.Join(dir, ".git", "hooks", "post-commit")

	// Write a hook that's not ours
	if err := os.WriteFile(hookPath, []byte("#!/bin/sh\necho hello\n"), 0o755); err != nil {
		t.Fatal(err)
	}

	if err := hookUninstallCmd.RunE(hookUninstallCmd, nil); err != nil {
		t.Fatalf("uninstall should not return error: %v", err)
	}

	// File should still exist since it's not ours
	if _, err := os.Stat(hookPath); os.IsNotExist(err) {
		t.Error("expected non-rekipedia hook to be left intact")
	}
}

func TestHookStatusInstalled(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir
	hookPath := filepath.Join(dir, ".git", "hooks", "post-commit")

	if err := os.WriteFile(hookPath, []byte(rekipediaHookContent), 0o755); err != nil {
		t.Fatal(err)
	}

	// Should not error
	if err := hookStatusCmd.RunE(hookStatusCmd, nil); err != nil {
		t.Fatalf("status failed: %v", err)
	}
}

func TestHookStatusNotInstalled(t *testing.T) {
	dir := makeGitDir(t)
	hookRepo = dir

	// Should not error even when hook doesn't exist
	if err := hookStatusCmd.RunE(hookStatusCmd, nil); err != nil {
		t.Fatalf("status failed: %v", err)
	}
}
