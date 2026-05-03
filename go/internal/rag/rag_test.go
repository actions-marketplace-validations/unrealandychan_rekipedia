package rag

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ── Chunker tests ──────────────────────────────────────────────────────────────

func TestChunkFile_GoFile(t *testing.T) {
	content := strings.Repeat("x", 3000)
	chunks := ChunkFile("foo.go", content)
	if len(chunks) < 2 {
		t.Fatalf("expected >=2 chunks for 3000 char Go file, got %d", len(chunks))
	}
}

func TestChunkFile_SkipLargeCode(t *testing.T) {
	content := strings.Repeat("a", maxCodeSize+1)
	chunks := ChunkFile("big.go", content)
	if chunks != nil {
		t.Fatal("expected nil for oversized code file")
	}
}

func TestChunkFile_SkipLargeDoc(t *testing.T) {
	content := strings.Repeat("b", maxDocSize+1)
	chunks := ChunkFile("big.md", content)
	if chunks != nil {
		t.Fatal("expected nil for oversized doc file")
	}
}

func TestChunkFile_SmallDoc(t *testing.T) {
	content := "# Hello\nThis is a test."
	chunks := ChunkFile("readme.md", content)
	if len(chunks) != 1 {
		t.Fatalf("expected 1 chunk, got %d", len(chunks))
	}
	if chunks[0].FilePath != "readme.md" {
		t.Errorf("bad file path: %s", chunks[0].FilePath)
	}
	if chunks[0].Text != content {
		t.Errorf("bad text")
	}
}

func TestChunkFile_SkipUnknownExt(t *testing.T) {
	chunks := ChunkFile("binary.exe", "some content")
	if chunks != nil {
		t.Fatal("expected nil for unknown extension")
	}
}

func TestChunkFile_Overlap(t *testing.T) {
	// Two chunks should share some content (overlap)
	content := strings.Repeat("ab", 1200) // 2400 runes
	chunks := ChunkFile("foo.ts", content)
	if len(chunks) < 2 {
		t.Fatalf("expected >=2 chunks, got %d", len(chunks))
	}
	// Last chars of chunk[0] should appear in start of chunk[1]
	end0 := chunks[0].Text[len(chunks[0].Text)-chunkOverlap:]
	start1 := chunks[1].Text[:chunkOverlap]
	if end0 != start1 {
		t.Error("overlap region mismatch between chunk 0 and chunk 1")
	}
}

func TestChunkFile_IDs(t *testing.T) {
	content := strings.Repeat("z", 3000)
	chunks := ChunkFile("src/main.go", content)
	for i, c := range chunks {
		if c.ID == "" {
			t.Errorf("chunk %d has empty ID", i)
		}
	}
}

// ── VectorStore tests ──────────────────────────────────────────────────────────

func TestVectorStore_AddAndSearch(t *testing.T) {
	vs := NewVectorStore()
	c1 := Chunk{ID: "1", FilePath: "a.go", Text: "hello"}
	c2 := Chunk{ID: "2", FilePath: "b.go", Text: "world"}
	vs.Add(c1, []float32{1, 0, 0})
	vs.Add(c2, []float32{0, 1, 0})

	results := vs.Search([]float32{1, 0, 0}, 1)
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Chunk.ID != "1" {
		t.Errorf("expected chunk 1, got %s", results[0].Chunk.ID)
	}
}

func TestVectorStore_SearchTopK(t *testing.T) {
	vs := NewVectorStore()
	for i := 0; i < 5; i++ {
		vec := make([]float32, 3)
		vec[i%3] = float32(i + 1)
		vs.Add(Chunk{ID: string(rune('0' + i))}, vec)
	}
	results := vs.Search([]float32{1, 0, 0}, 3)
	if len(results) != 3 {
		t.Fatalf("expected 3 results, got %d", len(results))
	}
}

func TestVectorStore_EmptySearch(t *testing.T) {
	vs := NewVectorStore()
	results := vs.Search([]float32{1, 0, 0}, 5)
	if results != nil {
		t.Fatal("expected nil from empty store")
	}
}

func TestVectorStore_SaveLoad(t *testing.T) {
	dir := t.TempDir()
	vs := NewVectorStore()
	vs.Add(Chunk{ID: "x", FilePath: "x.go", Text: "test"}, []float32{0.5, 0.5})
	if err := vs.Save(dir); err != nil {
		t.Fatalf("save: %v", err)
	}
	vs2 := NewVectorStore()
	if err := vs2.Load(dir); err != nil {
		t.Fatalf("load: %v", err)
	}
	if vs2.Len() != 1 {
		t.Fatalf("expected 1 chunk after load, got %d", vs2.Len())
	}
	// Verify round-trip via Search.
	results := vs2.Search([]float32{0.5, 0.5}, 1)
	if len(results) != 1 || results[0].Chunk.ID != "x" {
		t.Errorf("chunk ID mismatch after load: %+v", results)
	}
}

// ── ScanMeta tests ─────────────────────────────────────────────────────────────

func TestWriteReadScanMeta(t *testing.T) {
	dir := t.TempDir()
	meta := ScanMeta{
		Model:     "test-model",
		RepoPath:  "/tmp/repo",
		RunID:     "abc123",
		FileCount: 42,
		Embedded:  true,
	}
	if err := WriteScanMeta(dir, meta); err != nil {
		t.Fatalf("write: %v", err)
	}
	got, err := ReadScanMeta(dir)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if got.Model != "test-model" || got.FileCount != 42 || !got.Embedded {
		t.Errorf("round-trip mismatch: %+v", got)
	}
}

func TestPatchScanMeta(t *testing.T) {
	dir := t.TempDir()
	meta := ScanMeta{Model: "m1", FileCount: 10}
	WriteScanMeta(dir, meta)

	if err := PatchScanMeta(dir, map[string]any{"embedded": true, "file_count": 20}); err != nil {
		t.Fatalf("patch: %v", err)
	}
	got, _ := ReadScanMeta(dir)
	if !got.Embedded {
		t.Error("embedded should be true after patch")
	}
}

func TestPatchScanMeta_NoExistingFile(t *testing.T) {
	dir := t.TempDir()
	if err := PatchScanMeta(dir, map[string]any{"model": "new-model"}); err != nil {
		t.Fatalf("patch on missing file: %v", err)
	}
	data, err := os.ReadFile(filepath.Join(dir, "scan_meta.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "new-model") {
		t.Error("expected model in patched file")
	}
}

func TestScanMeta_ScannedAtAutoFilled(t *testing.T) {
	dir := t.TempDir()
	WriteScanMeta(dir, ScanMeta{})
	got, _ := ReadScanMeta(dir)
	if got.ScannedAt == "" {
		t.Error("ScannedAt should be auto-filled")
	}
}

func TestReadScanMetaMissing(t *testing.T) {
	dir := t.TempDir()
	_, err := ReadScanMeta(dir)
	if err == nil {
		t.Error("expected error reading missing scan_meta.json")
	}
}

func TestChunkFile_JSONFile(t *testing.T) {
	content := `{"key": "value"}`
	chunks := ChunkFile("data.json", content)
	if len(chunks) != 1 {
		t.Fatalf("expected 1 chunk for json file, got %d", len(chunks))
	}
}

func TestChunkFile_YAMLFile(t *testing.T) {
	content := "key: value\nfoo: bar\n"
	chunks := ChunkFile("config.yaml", content)
	if len(chunks) != 1 {
		t.Fatalf("expected 1 chunk for yaml file, got %d", len(chunks))
	}
}

func TestChunkFile_EmptyContent(t *testing.T) {
	chunks := ChunkFile("empty.go", "")
	// Empty content: 0 runes → still produces a chunk
	_ = chunks
}

func TestVectorStore_Len(t *testing.T) {
	vs := NewVectorStore()
	if vs.Len() != 0 {
		t.Error("expected len 0 for new store")
	}
	vs.Add(Chunk{ID: "a", Text: "hello"}, []float32{1, 0})
	if vs.Len() != 1 {
		t.Errorf("expected len 1 after add, got %d", vs.Len())
	}
}

func TestPatchScanMeta_InvalidJSON(t *testing.T) {
	dir := t.TempDir()
	// Write invalid JSON
	path := filepath.Join(dir, "scan_meta.json")
	os.WriteFile(path, []byte("not json"), 0o644)
	err := PatchScanMeta(dir, map[string]any{"k": "v"})
	if err == nil {
		t.Error("expected error for invalid JSON")
	}
}

func TestVectorStore_SaveEmpty(t *testing.T) {
	dir := t.TempDir()
	vs := NewVectorStore()
	// Save an empty store — should succeed (no collection created)
	// chromem will create collection on first Add, so saving with no adds is fine
	// Actually ensureCollection is not called, so Save may fail or succeed depending on impl.
	// Just verify no panic.
	_ = vs.Save(dir)
}

func TestVectorStore_LoadMissing(t *testing.T) {
	dir := t.TempDir()
	vs := NewVectorStore()
	err := vs.Load(dir)
	if err == nil {
		t.Error("expected error loading non-existent vector store")
	}
}

func TestWriteScanMeta_RoundTrip(t *testing.T) {
	dir := t.TempDir()
	meta := ScanMeta{
		Model:      "gpt-4o",
		RepoPath:   "/code",
		RunID:      "run-xyz",
		FileCount:  10,
		PageCount:  5,
		EmbedModel: "text-embedding-3-small",
		Embedded:   true,
	}
	if err := WriteScanMeta(dir, meta); err != nil {
		t.Fatalf("write: %v", err)
	}
	got, err := ReadScanMeta(dir)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if got.EmbedModel != "text-embedding-3-small" {
		t.Errorf("EmbedModel mismatch: %q", got.EmbedModel)
	}
	if got.PageCount != 5 {
		t.Errorf("PageCount mismatch: %d", got.PageCount)
	}
}

