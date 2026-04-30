package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Version != 1 {
		t.Errorf("expected version 1, got %d", cfg.Version)
	}
	if cfg.LLM.Model != "ollama/llama4" {
		t.Errorf("expected model ollama/llama4, got %s", cfg.LLM.Model)
	}
	if len(cfg.Ignore) == 0 {
		t.Error("expected non-empty ignore list")
	}
}

func TestLoadMissingFile(t *testing.T) {
	tmp := t.TempDir()
	cfg, err := Load(tmp)
	if err != nil {
		t.Fatalf("Load returned error for missing config: %v", err)
	}
	// Should fall back to defaults
	if cfg.LLM.Model != "ollama/llama4" {
		t.Errorf("expected default model, got %s", cfg.LLM.Model)
	}
}

func TestLoadFromFile(t *testing.T) {
	tmp := t.TempDir()
	dir := filepath.Join(tmp, ".close-wiki")
	_ = os.MkdirAll(dir, 0o755)
	yaml := "version: 1\nllm:\n  model: gpt-4o\n  temperature: 0.5\n"
	_ = os.WriteFile(filepath.Join(dir, "config.yml"), []byte(yaml), 0o644)

	cfg, err := Load(tmp)
	if err != nil {
		t.Fatalf("Load error: %v", err)
	}
	if cfg.LLM.Model != "gpt-4o" {
		t.Errorf("expected gpt-4o, got %s", cfg.LLM.Model)
	}
	if cfg.LLM.Temperature != 0.5 {
		t.Errorf("expected temperature 0.5, got %f", cfg.LLM.Temperature)
	}
}

func TestEnvOverride(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("CLOSE_WIKI_MODEL", "claude-opus-4")
	t.Setenv("CLOSE_WIKI_API_KEY", "sk-test")
	t.Setenv("CLOSE_WIKI_EMBED_PROVIDER", "openai")

	cfg, _ := Load(tmp)
	if cfg.LLM.Model != "claude-opus-4" {
		t.Errorf("env override failed: got %s", cfg.LLM.Model)
	}
	if cfg.LLM.APIKey != "sk-test" {
		t.Errorf("api_key override failed")
	}
	if cfg.LLM.EmbedProvider != "openai" {
		t.Errorf("embed_provider override failed")
	}
}

func TestInitDir(t *testing.T) {
	tmp := t.TempDir()
	if err := InitDir(tmp); err != nil {
		t.Fatalf("InitDir error: %v", err)
	}
	cfgPath := filepath.Join(tmp, ".close-wiki", "config.yml")
	if _, err := os.Stat(cfgPath); err != nil {
		t.Errorf("config.yml not created: %v", err)
	}
}

func TestInitDirIdempotent(t *testing.T) {
	tmp := t.TempDir()
	_ = InitDir(tmp)
	// Second call should not error
	if err := InitDir(tmp); err != nil {
		t.Fatalf("second InitDir call failed: %v", err)
	}
}
