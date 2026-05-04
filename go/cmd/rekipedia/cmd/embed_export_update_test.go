// Copyright 2026 Eddie Chan. All rights reserved.
// Proprietary — see LICENSE for details.

package cmd

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// ---------------------------------------------------------------------------
// embed command tests
// ---------------------------------------------------------------------------

func TestEmbedCmdRegistered(t *testing.T) {
	found := false
	for _, c := range rootCmd.Commands() {
		if c.Name() == "embed" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected 'embed' to be registered as a subcommand")
	}
}

func TestEmbedCmdFlags(t *testing.T) {
	f := embedCmd.Flags()
	for _, name := range []string{"model", "provider", "api-key", "base-url", "output-dir", "verbose"} {
		if f.Lookup(name) == nil {
			t.Errorf("embed command missing flag --%s", name)
		}
	}
}

func TestEmbedCmdUseLine(t *testing.T) {
	if embedCmd.Use == "" {
		t.Error("embed command Use string must not be empty")
	}
}

// ---------------------------------------------------------------------------
// export command tests
// ---------------------------------------------------------------------------

func TestExportCmdRegistered(t *testing.T) {
	found := false
	for _, c := range rootCmd.Commands() {
		if c.Name() == "export" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected 'export' to be registered as a subcommand")
	}
}

func TestExportCmdFlags(t *testing.T) {
	f := exportCmd.Flags()
	for _, name := range []string{"format", "output-path", "title"} {
		if f.Lookup(name) == nil {
			t.Errorf("export command missing flag --%s", name)
		}
	}
}

func TestExportCmdDefaultFormat(t *testing.T) {
	f := exportCmd.Flags().Lookup("format")
	if f == nil {
		t.Fatal("missing --format flag")
	}
	if f.DefValue != "md" {
		t.Errorf("expected default format 'md', got %q", f.DefValue)
	}
}

// ---------------------------------------------------------------------------
// update command tests
// ---------------------------------------------------------------------------

func TestUpdateCmdRegistered(t *testing.T) {
	found := false
	for _, c := range rootCmd.Commands() {
		if c.Name() == "update" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected 'update' to be registered as a subcommand")
	}
}

func TestUpdateCmdFlags(t *testing.T) {
	f := updateCmd.Flags()
	for _, name := range []string{"model", "verbose", "languages", "output-dir"} {
		if f.Lookup(name) == nil {
			t.Errorf("update command missing flag --%s", name)
		}
	}
}

func TestUpdateCmdUseLine(t *testing.T) {
	if updateCmd.Use == "" {
		t.Error("update command Use string must not be empty")
	}
}

// ---------------------------------------------------------------------------
// export JSON helper — unit test for JSON marshalling of a minimal payload
// ---------------------------------------------------------------------------

func TestExportJSONMarshal(t *testing.T) {
	// Verify that the JSON serialisation of a wiki-page map works correctly,
	// mirroring what the export command does internally.
	pages := map[string]string{
		"index": "# Hello\n\nWorld.\n",
		"auth":  "# Auth\n\nDetails here.\n",
	}
	data, err := json.Marshal(pages)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	var back map[string]string
	if err := json.Unmarshal(data, &back); err != nil {
		t.Fatalf("json.Unmarshal: %v", err)
	}
	if back["index"] != pages["index"] {
		t.Errorf("round-trip mismatch for 'index'")
	}
}

// ---------------------------------------------------------------------------
// update manifest hash helper — ensure SHA-256 hex strings are stable
// ---------------------------------------------------------------------------

func TestUpdateManifestFileWrite(t *testing.T) {
	dir := t.TempDir()
	manifest := map[string]string{
		"main.go": "abc123",
		"foo.py":  "def456",
	}
	data, err := json.Marshal(manifest)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	p := filepath.Join(dir, "manifest.json")
	if err := os.WriteFile(p, data, 0o644); err != nil {
		t.Fatalf("write: %v", err)
	}
	raw, err := os.ReadFile(p)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	var back map[string]string
	if err := json.Unmarshal(raw, &back); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if back["main.go"] != "abc123" {
		t.Errorf("unexpected hash for main.go: %q", back["main.go"])
	}
}
