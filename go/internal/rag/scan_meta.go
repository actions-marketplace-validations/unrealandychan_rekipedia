package rag

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// ScanMeta holds metadata about the last scan/embed run.
type ScanMeta struct {
	Model      string `json:"model"`
	ScannedAt  string `json:"scanned_at"`
	RepoPath   string `json:"repo_path"`
	RunID      string `json:"run_id"`
	FileCount  int    `json:"file_count"`
	PageCount  int    `json:"page_count"`
	EmbedModel string `json:"embed_model"`
	Embedded   bool   `json:"embedded"`
}

// WriteScanMeta serialises meta to outputDir/scan_meta.json.
func WriteScanMeta(outputDir string, meta ScanMeta) error {
	if meta.ScannedAt == "" {
		meta.ScannedAt = time.Now().UTC().Format(time.RFC3339)
	}
	data, err := json.MarshalIndent(meta, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(outputDir, "scan_meta.json"), data, 0o644)
}

// ReadScanMeta loads outputDir/scan_meta.json.
func ReadScanMeta(outputDir string) (*ScanMeta, error) {
	data, err := os.ReadFile(filepath.Join(outputDir, "scan_meta.json"))
	if err != nil {
		return nil, err
	}
	var meta ScanMeta
	if err := json.Unmarshal(data, &meta); err != nil {
		return nil, err
	}
	return &meta, nil
}

// PatchScanMeta reads, merges, and writes back scan_meta.json.
func PatchScanMeta(outputDir string, updates map[string]any) error {
	path := filepath.Join(outputDir, "scan_meta.json")
	var raw map[string]any

	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			raw = map[string]any{}
		} else {
			return err
		}
	} else {
		if err := json.Unmarshal(data, &raw); err != nil {
			return fmt.Errorf("unmarshal scan_meta: %w", err)
		}
	}

	for k, v := range updates {
		raw[k] = v
	}

	out, err := json.MarshalIndent(raw, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, out, 0o644)
}
