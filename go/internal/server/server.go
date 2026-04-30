// Package server provides the close-wiki HTTP server.
package server

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"html/template"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/yuin/goldmark"

	"github.com/unrealandychan/close-wiki/internal/models"
	"github.com/unrealandychan/close-wiki/internal/orchestrator"
)

// Server serves the close-wiki web UI.
type Server struct {
	repoRoot  string
	outputDir string
	llmCfg    models.LLMConfig
	addr      string
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
	r.Get("/api/pages", s.handleAPIPages)
	r.Get("/api/page/{slug}", s.handleAPIPage)
	r.Post("/api/ask", s.handleAPIAsk)
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

// ── handlers ──────────────────────────────────────────────────────────────────

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	pages := s.listPages()
	if len(pages) == 0 {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, "<html><body><h1>No wiki yet</h1><p>Run <code>close-wiki scan .</code> first.</p></body></html>")
		return
	}
	http.Redirect(w, r, "/wiki/"+pages[0].Slug, http.StatusFound)
}

func (s *Server) handleWikiPage(w http.ResponseWriter, r *http.Request) {
	slug := chi.URLParam(r, "slug")
	mdPath := filepath.Join(s.outputDir, "wiki", slug+".md")
	data, err := os.ReadFile(mdPath)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	var buf bytes.Buffer
	if err := goldmark.Convert(data, &buf); err != nil {
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

	tmpl := template.Must(template.New("page").Parse(htmlTemplate))
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	tmpl.Execute(w, map[string]any{
		"Title":   title,
		"Content": template.HTML(buf.String()),
		"Pages":   pages,
		"Slug":    slug,
	})
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

func (s *Server) handleAPIAsk(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Question string `json:"question"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad request", 400)
		return
	}
	result, err := orchestrator.RunAsk(r.Context(), req.Question, s.repoRoot, s.outputDir, orchestrator.AskOptions{
		LLMConfig: s.llmCfg,
	})
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	writeJSON(w, map[string]string{"answer": result.Answer})
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"status": "ok"})
}

// ── helpers ───────────────────────────────────────────────────────────────────

type pageInfo struct {
	Slug  string `json:"slug"`
	Title string `json:"title"`
}

func (s *Server) listPages() []pageInfo {
	wikiDir := filepath.Join(s.outputDir, "wiki")
	entries, err := os.ReadDir(wikiDir)
	if err != nil {
		return nil
	}
	var pages []pageInfo
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
		pages = append(pages, pageInfo{Slug: slug, Title: title})
	}
	sort.Slice(pages, func(i, j int) bool { return pages[i].Slug < pages[j].Slug })
	return pages
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}

// htmlTemplate is the full-page HTML template (dark theme).
const htmlTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{.Title}} — close-wiki</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#1a1a2e;color:#e0e0e0;display:flex;height:100vh;overflow:hidden}
#sidebar{width:240px;background:#16213e;padding:16px;overflow-y:auto;flex-shrink:0;border-right:1px solid #0f3460}
#sidebar h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#a0a0b0;margin-bottom:12px}
#sidebar a{display:block;padding:6px 8px;border-radius:4px;color:#c0c8e8;text-decoration:none;font-size:14px;margin-bottom:2px}
#sidebar a:hover,#sidebar a.active{background:#0f3460;color:#e0e8ff}
#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
#content{flex:1;padding:32px 40px;overflow-y:auto;max-width:860px}
h1,h2,h3{color:#e8eaf6;margin:1.2em 0 .5em}
p{line-height:1.7;margin-bottom:1em}
code{background:#0d1b2a;padding:2px 6px;border-radius:3px;font-size:90%;color:#80cbc4}
pre{background:#0d1b2a;padding:16px;border-radius:6px;overflow-x:auto;margin-bottom:1em}
pre code{background:none;padding:0}
#ask{background:#16213e;border-top:1px solid #0f3460;padding:12px 16px;display:flex;gap:8px}
#ask input{flex:1;background:#1a1a2e;border:1px solid #0f3460;color:#e0e0e0;padding:8px 12px;border-radius:4px;font-size:14px}
#ask button{background:#0f3460;color:#e0e8ff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-size:14px}
#ask button:hover{background:#1a5276}
#answer{padding:12px 16px;background:#0d1b2a;border-top:1px solid #0f3460;font-size:14px;white-space:pre-wrap;max-height:200px;overflow-y:auto;display:none}
</style>
</head>
<body>
<nav id="sidebar">
  <h2>close-wiki</h2>
  {{range .Pages}}
  <a href="/wiki/{{.Slug}}"{{if eq $.Slug .Slug}} class="active"{{end}}>{{.Title}}</a>
  {{end}}
</nav>
<div id="main">
  <div id="content">{{.Content}}</div>
  <div id="ask">
    <input id="q" type="text" placeholder="Ask a question…">
    <button onclick="ask()">Ask</button>
  </div>
  <div id="answer"></div>
</div>
<script>
async function ask(){
  const q=document.getElementById('q').value.trim();
  if(!q)return;
  const ans=document.getElementById('answer');
  ans.style.display='block';
  ans.textContent='Thinking…';
  try{
    const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
    const d=await r.json();
    ans.textContent=d.answer||d.error||'No answer.';
  }catch(e){ans.textContent='Error: '+e.message;}
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')ask();});
</script>
</body>
</html>`
