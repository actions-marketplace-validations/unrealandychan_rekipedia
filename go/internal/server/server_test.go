package server

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/unrealandychan/rekipedia/internal/models"
	"github.com/unrealandychan/rekipedia/internal/storage"
)

func makeTestServer(t *testing.T) (*Server, string) {
	dir := t.TempDir()
	wikiDir := filepath.Join(dir, "wiki")
	os.MkdirAll(wikiDir, 0o755)
	// Write a sample wiki page
	os.WriteFile(filepath.Join(wikiDir, "overview.md"), []byte("# Overview\nThis is the overview."), 0o644)
	s := New(".", dir, ":0", models.DefaultLLMConfig())
	return s, dir
}

func TestHealth(t *testing.T) {
	s, _ := makeTestServer(t)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/health", nil)
	s.handleHealth(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var resp map[string]string
	json.NewDecoder(rec.Body).Decode(&resp)
	if resp["status"] != "ok" {
		t.Errorf("expected status ok, got %v", resp)
	}
}

func TestAPIPages(t *testing.T) {
	s, _ := makeTestServer(t)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/pages", nil)
	s.handleAPIPages(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var pages []pageInfo
	json.NewDecoder(rec.Body).Decode(&pages)
	if len(pages) == 0 {
		t.Fatal("expected at least one page")
	}
	if pages[0].Slug != "overview" {
		t.Errorf("unexpected slug: %s", pages[0].Slug)
	}
}

func TestAPIPageNotFound(t *testing.T) {
	s, _ := makeTestServer(t)

	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/page/nonexistent", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 404 {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestAPIPageFound(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/page/overview", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var resp map[string]any
	json.NewDecoder(rec.Body).Decode(&resp)
	if resp["slug"] != "overview" {
		t.Errorf("slug mismatch")
	}
	if !strings.Contains(resp["content"].(string), "Overview") {
		t.Error("content missing")
	}
}

func TestWikiPageRendered(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/wiki/overview", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	body := rec.Body.String()
	if !strings.Contains(body, "<h1") {
		t.Error("expected rendered HTML h1 in wiki page")
	}
}

func TestIndexRedirects(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/", nil)
	r.ServeHTTP(rec, req)
	// Index now renders a dashboard page (200) when wiki pages exist
	if rec.Code != 200 {
		t.Fatalf("expected 200 dashboard, got %d", rec.Code)
	}
}

func TestAPIAskBadJSON(t *testing.T) {
	s, _ := makeTestServer(t)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("POST", "/api/ask", bytes.NewBufferString("not-json"))
	s.handleAPIAsk(rec, req)
	if rec.Code != 400 {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

// makeRouter builds the chi router the same way Start() does.
func makeRouter(s *Server) http.Handler {
	r := newRouter(s)
	return r
}

func TestAPIGraph(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/graph", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	for _, key := range []string{"nodes", "edges", "god_nodes"} {
		if _, ok := resp[key]; !ok {
			t.Errorf("missing key %q in graph response", key)
		}
	}
}

func TestGraphPage(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/graph", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestWikiPageInvalidSlug(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/wiki/../../etc/passwd", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 404 {
		t.Errorf("expected 404 for path-traversal slug, got %d", rec.Code)
	}
}

func TestWikiPageMissing(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/wiki/nonexistent-page", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 404 {
		t.Errorf("expected 404 for missing wiki page, got %d", rec.Code)
	}
}

func TestAPIPagesJSON(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/pages", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var pages []map[string]any
	if err := json.NewDecoder(rec.Body).Decode(&pages); err != nil {
		t.Fatalf("expected JSON array: %v", err)
	}
}

func TestAPIHealthJSON(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/health", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var resp map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("expected JSON: %v", err)
	}
	if resp["status"] == "" {
		t.Error("missing status field")
	}
}

func TestAPIHistoryEmpty(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/history", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestDiagramNotFound(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/diagrams/nonexistent.png", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 404 {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestAskStreamMissingQuestion(t *testing.T) {
	s, _ := makeTestServer(t)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("POST", "/ask/stream", bytes.NewBufferString(`{}`))
	s.handleAskStream(rec, req)
	if rec.Code != 400 {
		t.Errorf("expected 400 for empty question, got %d", rec.Code)
	}
}

func TestAskPageRendered(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/ask", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestAPIAskStreamMissingQuestion(t *testing.T) {
	s, _ := makeTestServer(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/ask/stream", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 400 {
		t.Errorf("expected 400 for missing question, got %d", rec.Code)
	}
}

func TestListPagesEmpty(t *testing.T) {
	dir := t.TempDir()
	s := New(".", dir, ":0", models.DefaultLLMConfig())
	pages := s.listPages()
	if pages != nil {
		// No wiki dir → nil is fine
	}
	_ = pages
}

func makeTestServerWithStore(t *testing.T) (*Server, string) {
	dir := t.TempDir()
	// Create wiki dir
	wikiDir := filepath.Join(dir, "wiki")
	os.MkdirAll(wikiDir, 0o755)
	os.WriteFile(filepath.Join(wikiDir, "overview.md"), []byte("# Overview\nContent."), 0o644)

	// Create a store with run data
	dbPath := filepath.Join(dir, "store.db")
	store, err := storage.Open(dbPath)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	_ = store.CreateRun("run-1", ".", "test-model")
	_ = store.FinishRun("run-1", 1)
	store.Close()

	s := New(".", dir, ":0", models.DefaultLLMConfig())
	return s, dir
}

func TestGatherStatsWithStore(t *testing.T) {
	s, _ := makeTestServerWithStore(t)
	stats := s.gatherStats()
	if stats.RunID == "—" {
		t.Error("expected RunID to be set from store")
	}
}

func TestAPIGraphWithStore(t *testing.T) {
	s, _ := makeTestServerWithStore(t)
	r := makeRouter(s)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/api/graph", nil)
	r.ServeHTTP(rec, req)
	if rec.Code != 200 {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var resp map[string]any
	json.NewDecoder(rec.Body).Decode(&resp)
	if _, ok := resp["nodes"]; !ok {
		t.Error("missing nodes key")
	}
}
