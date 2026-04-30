// Package orchestrator — RunDigest is the full scan pipeline.
package orchestrator

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/fatih/color"
	"github.com/google/uuid"
	"github.com/schollz/progressbar/v3"
	"golang.org/x/sync/errgroup"

	"github.com/unrealandychan/close-wiki/internal/extractor"
	"github.com/unrealandychan/close-wiki/internal/llm"
	"github.com/unrealandychan/close-wiki/internal/models"
	"github.com/unrealandychan/close-wiki/internal/storage"
	"github.com/unrealandychan/close-wiki/internal/synthesis"
)

const maxShardWorkers = 4

// DigestOptions configures a full scan run.
type DigestOptions struct {
	LLMConfig models.LLMConfig
	Verbose   bool
	Progress  func(string) // optional progress callback
	Languages []string     // nil = all languages
}

// RunDigest executes the full scan → plan → generate → export pipeline.
//
// Flow:
//  1. Snapshot repo
//  2. Shard files
//  3. Extract shards in parallel
//  4. Build diagrams
//  5. Plan wiki structure (LLM)
//  6. Generate wiki pages (LLM, concurrent)
//  7. Persist & export
func RunDigest(ctx context.Context, repoRoot, outputDir string, opts DigestOptions) error {
	log := newProgressLogger(opts.Progress, opts.Verbose)

	runID := uuid.New().String()
	dbPath := filepath.Join(outputDir, "store.db")

	store, err := storage.Open(dbPath)
	if err != nil {
		return fmt.Errorf("open store: %w", err)
	}
	defer store.Close()

	if err := store.UpsertRun(runID, repoRoot); err != nil {
		return fmt.Errorf("upsert run: %w", err)
	}
	log.logf("Run %s started", runID[:8])

	// ── 1. Snapshot ────────────────────────────────────────────────────────
	log.logf("Snapshotting repository…")
	snapper := NewSnapshotter(repoRoot, nil, opts.Languages)
	files, err := snapper.Snapshot()
	if err != nil {
		return fmt.Errorf("snapshot: %w", err)
	}
	log.logf("  %d files found", len(files))

	if err := store.UpsertSnapshot(runID, files); err != nil {
		return fmt.Errorf("store snapshot: %w", err)
	}

	// ── 2. Shard ───────────────────────────────────────────────────────────
	log.logf("Planning shards…")
	planner := NewShardPlanner(0)
	shards := planner.Plan(files)
	log.logf("  %d shards planned", len(shards))

	// ── 3. Extract shards in parallel ──────────────────────────────────────
	log.logf("Extracting shards (up to %d parallel)…", maxShardWorkers)
	mergedResults := make([]models.AnalysisResult, len(shards))
	var resultsMu sync.Mutex

	sem := make(chan struct{}, maxShardWorkers)
	eg, egCtx := errgroup.WithContext(ctx)

	reg := extractor.NewRegistry()
	bar := newShardBar(len(shards))

	for i, shard := range shards {
		i, shard := i, shard
		eg.Go(func() error {
			sem <- struct{}{}
			defer func() { <-sem }()

			result, err := extractShard(egCtx, repoRoot, shard, reg)
			resultsMu.Lock()
			defer resultsMu.Unlock()
			_ = bar.Add(1)
			if err != nil {
				log.logf("  ⚠ shard %s failed: %v", shard.ShardID, err)
				mergedResults[i] = models.AnalysisResult{
					ShardID:     shard.ShardID,
					FilesSeen:   []string{},
					EntryPoints: []string{},
					Risks:       []string{fmt.Sprintf("extraction failed: %v", err)},
				}
				return nil // graceful — don't abort the whole run
			}
			mergedResults[i] = result
			log.logf("  ✓ %s: %d symbols, %d rels", shard.ShardID, len(result.Symbols), len(result.Relationships))
			return nil
		})
	}
	if err := eg.Wait(); err != nil {
		return err
	}

	// Persist results (SQLite writes must be serial)
	for _, result := range mergedResults {
		if err := store.UpsertSymbols(runID, result.Symbols); err != nil {
			return fmt.Errorf("store symbols: %w", err)
		}
		if err := store.UpsertRelationships(runID, result.Relationships); err != nil {
			return fmt.Errorf("store rels: %w", err)
		}
	}

	// ── 4. Combine + build diagrams ────────────────────────────────────────
	log.logf("Building diagrams…")
	combined := combineResults(mergedResults)
	db := synthesis.NewDiagramBuilder()
	diagrams := db.Build(combined.Relationships, combined.EntryPoints)
	log.logf("  %d diagram(s) built", len(diagrams))

	if mg, ok := diagrams["module-graph"]; ok {
		combined.Evidence["pre_built_module_graph"] = mg[1]
	}
	if ch, ok := diagrams["class-hierarchy"]; ok {
		combined.Evidence["pre_built_dependency_graph"] = ch[1]
	}

	// ── 5. Plan wiki structure ─────────────────────────────────────────────
	log.logf("Planning wiki structure…")
	llmClient := llm.New(opts.LLMConfig)
	wikiPlanner := synthesis.NewPlannerAgent(llmClient)
	plan, err := wikiPlanner.Plan(ctx, combined)
	if err != nil {
		return fmt.Errorf("plan wiki: %w", err)
	}
	log.logf("  %d pages planned", len(plan.Pages))

	// ── 6. Generate wiki pages ─────────────────────────────────────────────
	log.logf("Generating wiki pages…")
	pageBuilder := synthesis.NewPageBuilder(llmClient)
	diagMap := make(map[string][2]string)
	for k, v := range diagrams {
		diagMap[k] = [2]string(v)
	}
	pages, err := pageBuilder.BuildAll(ctx, plan, combined, diagMap)
	if err != nil {
		return fmt.Errorf("build pages: %w", err)
	}
	log.logf("  %d pages generated", len(pages))

	// ── 7. Persist pages & export ──────────────────────────────────────────
	log.logf("Persisting pages…")
	for slug, content := range pages {
		title := slug
		for _, spec := range plan.Pages {
			if spec.Slug == slug {
				title = spec.Title
				break
			}
		}
		if err := store.UpsertPage(runID, slug, title, content); err != nil {
			return fmt.Errorf("store page %q: %w", slug, err)
		}
	}

	// Export to disk
	wikiDir := filepath.Join(outputDir, "wiki")
	if err := os.MkdirAll(wikiDir, 0o755); err != nil {
		return fmt.Errorf("mkdir wiki: %w", err)
	}
	for slug, content := range pages {
		path := filepath.Join(wikiDir, slug+".md")
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			return fmt.Errorf("write page %q: %w", slug, err)
		}
	}

	log.logf("✅ Done — run %s | %d pages in %s", runID[:8], len(pages), outputDir)
	return nil
}

// ── helpers ───────────────────────────────────────────────────────────────────

func extractShard(_ context.Context, repoRoot string, shard models.Shard, reg *extractor.Registry) (models.AnalysisResult, error) {
	if reg == nil {
		reg = extractor.NewRegistry()
	}
	result := models.AnalysisResult{
		ShardID:   shard.ShardID,
		FilesSeen: make([]string, 0, len(shard.Files)),
		Evidence:  make(map[string]string),
	}

	for _, fm := range shard.Files {
		fullPath := filepath.Join(repoRoot, fm.Path)
		ext := filepath.Ext(fm.Path)
		ar := reg.ExtractFile(fullPath, fm.Path, ext)
		result.FilesSeen = append(result.FilesSeen, fm.Path)
		result = mergeInto(result, ar)
	}
	return result, nil
}

func mergeInto(base, extra models.AnalysisResult) models.AnalysisResult {
	base.Symbols = append(base.Symbols, extra.Symbols...)
	base.Relationships = append(base.Relationships, extra.Relationships...)
	base.EntryPoints = append(base.EntryPoints, extra.EntryPoints...)
	base.BuildCommands = append(base.BuildCommands, extra.BuildCommands...)
	base.TestCommands = append(base.TestCommands, extra.TestCommands...)
	base.Risks = append(base.Risks, extra.Risks...)
	for k, v := range extra.Evidence {
		base.Evidence[k] = v
	}
	return base
}

func combineResults(results []models.AnalysisResult) models.AnalysisResult {
	combined := models.AnalysisResult{Evidence: make(map[string]string)}
	for _, r := range results {
		combined.FilesSeen = append(combined.FilesSeen, r.FilesSeen...)
		combined.Symbols = append(combined.Symbols, r.Symbols...)
		combined.Relationships = append(combined.Relationships, r.Relationships...)
		combined.EntryPoints = append(combined.EntryPoints, r.EntryPoints...)
		combined.BuildCommands = append(combined.BuildCommands, r.BuildCommands...)
		combined.TestCommands = append(combined.TestCommands, r.TestCommands...)
		combined.Risks = append(combined.Risks, r.Risks...)
		for k, v := range r.Evidence {
			combined.Evidence[k] = v
		}
	}
	return combined
}

// progressLogger emits coloured messages to stderr and an optional callback.
type progressLogger struct {
	cb      func(string)
	verbose bool

	cyan    *color.Color
	green   *color.Color
	yellow  *color.Color
	red     *color.Color
}

func newProgressLogger(cb func(string), verbose bool) *progressLogger {
	return &progressLogger{
		cb:      cb,
		verbose: verbose,
		cyan:    color.New(color.FgCyan, color.Bold),
		green:   color.New(color.FgGreen),
		yellow:  color.New(color.FgYellow),
		red:     color.New(color.FgRed),
	}
}

func (l *progressLogger) logf(format string, args ...any) {
	msg := fmt.Sprintf(format, args...)
	if l.cb != nil {
		l.cb(msg)
	}
	// Colour by content
	switch {
	case strings.HasPrefix(msg, "⚠") || strings.HasPrefix(msg, "  ⚠"):
		l.yellow.Fprintln(os.Stderr, msg)
	case strings.HasPrefix(msg, "  ✓") || strings.HasPrefix(msg, "✅"):
		l.green.Fprintln(os.Stderr, msg)
	case strings.HasPrefix(msg, "Error") || strings.HasPrefix(msg, "error"):
		l.red.Fprintln(os.Stderr, msg)
	default:
		l.cyan.Fprintln(os.Stderr, msg)
	}
}

// newShardBar creates a progressbar for shard processing.
func newShardBar(total int) *progressbar.ProgressBar {
	return progressbar.NewOptions(total,
		progressbar.OptionSetDescription("  extracting shards"),
		progressbar.OptionSetWriter(os.Stderr),
		progressbar.OptionShowCount(),
		progressbar.OptionSetTheme(progressbar.Theme{
			Saucer:        "=",
			SaucerHead:    ">",
			SaucerPadding: " ",
			BarStart:      "[",
			BarEnd:        "]",
		}),
		progressbar.OptionClearOnFinish(),
	)
}
