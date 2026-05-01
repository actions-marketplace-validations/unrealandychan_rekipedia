// Package server provides the close-wiki HTTP server.
package server

import (
	"bytes"
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"html/template"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/yuin/goldmark"

	"github.com/unrealandychan/close-wiki/internal/models"
	"github.com/unrealandychan/close-wiki/internal/orchestrator"
	"github.com/unrealandychan/close-wiki/internal/storage"
)

//go:embed templates/*.html
var templateFS embed.FS

// Server serves the close-wiki web UI.
type Server struct {
	repoRoot  string
	outputDir string
	llmCfg    models.LLMConfig
	addr      string

	mu      sync.Mutex
	history []models.QAHistory
}

// New creates a new Server.
func New(repoRoot, outputDir, addr string, llmCfg models.LLMConfig) *Server {
	return &Server{repoRoot: repoRoot, outputDir: outputDir, llmCfg: llmCfg, addr: addr}
}

func newRouter(s *Server) *chi.Mux {
	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	r.Get("/", s.handleIndex)
	r.Get("/wiki/{slug}", s.handleWikiPage)
	r.Get("/ask", s.handleAskPage)
	r.Post("/ask/stream", s.handleAskStream)
	r.Get("/diagrams/{filename}", s.handleDiagram)
	r.Get("/api/pages", s.handleAPIPages)
	r.Get("/api/page/{slug}", s.handleAPIPage)
	r.Post("/api/ask", s.handleAPIAsk)
	r.Get("/api/ask/stream", s.handleAPIAskStream)
	r.Get("/api/history", s.handleAPIHistory)
	r.Get("/api/health", s.handleHealth)
	return r
}

// Start binds, serves requests, and blocks until ctx is cancelled.
func (s *Server) Start(ctx context.Context) error {
	r := newRouter(s)

	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return fmt.Errorf("listen %s: %w", s.addr, err)
	}

	srv := &http.Server{Handler: r}
	go func() {
		<-ctx.Done()
		srv.Close()
	}()

	fmt.Printf("close-wiki server listening on http://%s\n", ln.Addr())
	err = srv.Serve(ln)
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}

// ── template helpers ──────────────────────────────────────────────────────────

// templateFuncs provides helper functions used in templates.
var templateFuncs = template.FuncMap{
	"inc": func(i int) int { return i + 1 },
}

// loadTemplates parses all templates from the embedded FS.
func loadTemplates() (*template.Template, error) {
	tmpl := template.New("").Funcs(templateFuncs)
	return tmpl.ParseFS(templateFS, "templates/*.html")
}

// baseData returns common fields for all templates.
func (s *Server) baseData(activePage, activeSlug string) map[string]any {
	repoName := filepath.Base(s.repoRoot)
	pages := s.listPages()
	return map[string]any{
		"RepoName":   repoName,
		"RepoPath":   s.repoRoot,
		"ActivePage": activePage,
		"ActiveSlug": activeSlug,
		"Pages":      pages,
	}
}

// ── handlers ──────────────────────────────────────────────────────────────────

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	pages := s.listPages()

	// If no wiki exists yet, redirect to first page or show empty notice
	if len(pages) == 0 {
		http.Redirect(w, r, "/wiki/_empty", http.StatusFound)
		return
	}

	tmpl, err := loadTemplates()
	if err != nil {
		http.Error(w, "template error: "+err.Error(), 500)
		return
	}

	diagrams := s.listDiagrams()

	// Gather stats
	stats := s.gatherStats()

	data := s.baseData("home", "")
	data["Stats"] = stats
	data["Diagrams"] = diagrams

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := tmpl.ExecuteTemplate(w, "index.html", data); err != nil {
		http.Error(w, err.Error(), 500)
	}
}

func (s *Server) handleWikiPage(w http.ResponseWriter, r *http.Request) {
	slug := chi.URLParam(r, "slug")
	mdPath := filepath.Join(s.outputDir, "wiki", slug+".md")
	mdData, err := os.ReadFile(mdPath)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	var buf bytes.Buffer
	if err := goldmark.Convert(mdData, &buf); err != nil {
		http.Error(w, "render error", 500)
		return
	}

	pages := s.listPages()
	title := slug
	for _, p := range pages {
		if p.Slug == slug {
			title = p.Title
			break
		}
	}

	tmpl, err := loadTemplates()
	if err != nil {
		http.Error(w, "template error: "+err.Error(), 500)
		return
	}

	data := s.baseData("wiki", slug)
	data["Title"] = title
	data["Content"] = template.HTML(buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := tmpl.ExecuteTemplate(w, "wiki.html", data); err != nil {
		http.Error(w, err.Error(), 500)
	}
}

func (s *Server) handleAskPage(w http.ResponseWriter, r *http.Request) {
	tmpl, err := loadTemplates()
	if err != nil {
		http.Error(w, "template error: "+err.Error(), 500)
		return
	}

	data := s.baseData("ask", "")

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := tmpl.ExecuteTemplate(w, "ask.html", data); err != nil {
		http.Error(w, err.Error(), 500)
	}
}

func (s *Server) handleAskStream(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Question string `json:"question"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Question == "" {
		http.Error(w, "missing question", 400)
		return
	}

	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", 500)
		return
	}

	s.mu.Lock()
	histCopy := make([]models.QAHistory, len(s.history))
	copy(histCopy, s.history)
	s.mu.Unlock()

	var accumulated strings.Builder
	err := orchestrator.StreamAsk(r.Context(), req.Question, s.repoRoot, s.outputDir,
		orchestrator.AskOptions{LLMConfig: s.llmCfg, History: histCopy},
		func(chunk string) {
			accumulated.WriteString(chunk)
			safe := strings.ReplaceAll(chunk, "\n", `\n`)
			fmt.Fprintf(w, "data: %s\n\n", safe)
			flusher.Flush()
		},
	)
	if err != nil {
		fmt.Fprintf(w, "data: [ERROR] %s\n\n", err.Error())
	} else {
		fmt.Fprint(w, "data: [DONE]\n\n")
		answer := accumulated.String()
		s.persistQA(req.Question, answer)
	}
	flusher.Flush()
}

func (s *Server) handleAPIAskStream(w http.ResponseWriter, r *http.Request) {
	question := r.URL.Query().Get("question")
	if question == "" {
		http.Error(w, "missing question", 400)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", 500)
		return
	}

	s.mu.Lock()
	histCopy := make([]models.QAHistory, len(s.history))
	copy(histCopy, s.history)
	s.mu.Unlock()

	var accumulated strings.Builder
	err := orchestrator.StreamAsk(r.Context(), question, s.repoRoot, s.outputDir,
		orchestrator.AskOptions{LLMConfig: s.llmCfg, History: histCopy},
		func(chunk string) {
			accumulated.WriteString(chunk)
			safe := strings.ReplaceAll(chunk, "\n", `\n`)
			fmt.Fprintf(w, "data: %s\n\n", safe)
			flusher.Flush()
		},
	)
	if err != nil {
		fmt.Fprintf(w, "data: [ERROR] %s\n\n", err.Error())
	} else {
		fmt.Fprint(w, "data: [DONE]\n\n")
		s.persistQA(question, accumulated.String())
	}
	flusher.Flush()
}

func (s *Server) handleAPIAsk(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Question string `json:"question"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad request", 400)
		return
	}

	s.mu.Lock()
	histCopy := make([]models.QAHistory, len(s.history))
	copy(histCopy, s.history)
	s.mu.Unlock()

	result, err := orchestrator.RunAsk(r.Context(), req.Question, s.repoRoot, s.outputDir, orchestrator.AskOptions{
		LLMConfig: s.llmCfg,
		History:   histCopy,
	})
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	s.persistQA(req.Question, result.Answer)
	writeJSON(w, map[string]string{"answer": result.Answer})
}

func (s *Server) handleAPIHistory(w http.ResponseWriter, r *http.Request) {
	dbPath := filepath.Join(s.outputDir, "store.db")
	store, err := storage.Open(dbPath)
	if err != nil {
		writeJSON(w, []models.QAHistory{})
		return
	}
	defer store.Close()

	hist, err := store.GetQAHistory(s.repoRoot)
	if err != nil || hist == nil {
		writeJSON(w, []models.QAHistory{})
		return
	}
	writeJSON(w, hist)
}

func (s *Server) handleDiagram(w http.ResponseWriter, r *http.Request) {
	filename := chi.URLParam(r, "filename")
	// Prevent path traversal
	filename = filepath.Base(filename)
	fpath := filepath.Join(s.outputDir, "diagrams", filename)
	if _, err := os.Stat(fpath); err != nil {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, fpath)
}

func (s *Server) handleAPIPages(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, s.listPages())
}

func (s *Server) handleAPIPage(w http.ResponseWriter, r *http.Request) {
	slug := chi.URLParam(r, "slug")
	mdPath := filepath.Join(s.outputDir, "wiki", slug+".md")
	data, err := os.ReadFile(mdPath)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	title := slug
	pages := s.listPages()
	for _, p := range pages {
		if p.Slug == slug {
			title = p.Title
			break
		}
	}
	writeJSON(w, map[string]any{"slug": slug, "title": title, "content": string(data)})
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"status": "ok"})
}

// ── helpers ───────────────────────────────────────────────────────────────────

// persistQA saves Q&A to in-memory history and SQLite.
func (s *Server) persistQA(question, answer string) {
	entry := models.QAHistory{Question: question, Answer: answer}

	s.mu.Lock()
	s.history = append(s.history, entry)
	s.mu.Unlock()

	// Persist to SQLite (best effort)
	dbPath := filepath.Join(s.outputDir, "store.db")
	if store, err := storage.Open(dbPath); err == nil {
		defer store.Close()
		_ = store.SaveQAHistory(s.repoRoot, question, answer)
	}
}

type pageInfo struct {
	Slug  string `json:"slug"`
	Title string `json:"title"`
}

type statsInfo struct {
	PageCount   int    `json:"page_count"`
	SymbolCount int    `json:"symbol_count"`
	LastScan    string `json:"last_scan"`
	RunID       string `json:"run_id"`
}

func (s *Server) gatherStats() statsInfo {
	pages := s.listPages()
	info := statsInfo{
		PageCount: len(pages),
		LastScan:  "—",
		RunID:     "—",
	}

	dbPath := filepath.Join(s.outputDir, "store.db")
	store, err := storage.Open(dbPath)
	if err != nil {
		return info
	}
	defer store.Close()

	runID, err := store.GetLatestRunID(s.repoRoot)
	if err != nil || runID == "" {
		return info
	}
	info.RunID = runID

	syms, _ := store.GetAllSymbols(runID)
	info.SymbolCount = len(syms)

	// Try to get last scan time from run record
	var finishedAt string
	_ = store.QueryRunTime(runID, &finishedAt)
	if finishedAt != "" {
		if len(finishedAt) >= 16 {
			info.LastScan = strings.Replace(finishedAt[:16], "T", " ", 1)
		} else {
			info.LastScan = finishedAt
		}
	}
	return info
}

func (s *Server) listDiagrams() []string {
	diagDir := filepath.Join(s.outputDir, "diagrams")
	entries, err := os.ReadDir(diagDir)
	if err != nil {
		return nil
	}
	var files []string
	for _, e := range entries {
		if !e.IsDir() {
			files = append(files, e.Name())
		}
	}
	return files
}

func (s *Server) listPages() []pageInfo {
	wikiDir := filepath.Join(s.outputDir, "wiki")
	entries, err := os.ReadDir(wikiDir)
	if err != nil {
		return nil
	}

	available := make(map[string]string)
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".md") {
			continue
		}
		slug := strings.TrimSuffix(e.Name(), ".md")
		title := slug
		if data, err := os.ReadFile(filepath.Join(wikiDir, e.Name())); err == nil {
			for _, line := range strings.Split(string(data), "\n") {
				line = strings.TrimSpace(line)
				if strings.HasPrefix(line, "# ") {
					title = strings.TrimPrefix(line, "# ")
					break
				}
			}
		}
		available[slug] = title
	}

	var navOrder []string
	manifestPath := filepath.Join(s.outputDir, "exports", "manifest.json")
	if data, err := os.ReadFile(manifestPath); err == nil {
		var manifest struct {
			NavOrder []string `json:"nav_order"`
		}
		if err := json.Unmarshal(data, &manifest); err == nil {
			navOrder = manifest.NavOrder
		}
	}

	seen := make(map[string]bool)
	var orderedSlugs []string
	for _, slug := range navOrder {
		if _, ok := available[slug]; ok {
			orderedSlugs = append(orderedSlugs, slug)
			seen[slug] = true
		}
	}
	var remainder []string
	for slug := range available {
		if !seen[slug] {
			remainder = append(remainder, slug)
		}
	}
	sort.Strings(remainder)
	orderedSlugs = append(orderedSlugs, remainder...)

	var pages []pageInfo
	for _, slug := range orderedSlugs {
		pages = append(pages, pageInfo{Slug: slug, Title: available[slug]})
	}
	return pages
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}
