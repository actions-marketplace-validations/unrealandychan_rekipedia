"""Cross-repo search — fan-out across multiple SQLite stores."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _search_single_repo(db_path: Path, query: str) -> list[dict]:
    """Search symbols in one repo's DB. Returns list of match dicts."""
    try:
        from rekipedia.storage.sqlite_store import SqliteStore
        store = SqliteStore(db_path)
        run_id = store.latest_run_id()
        if not run_id:
            return []
        symbols = store.get_all_symbols(run_id)
        ql = query.lower()
        results = []
        for s in symbols:
            name = s.name if hasattr(s, 'name') else s.get('name', '')
            file = s.file if hasattr(s, 'file') else s.get('file', '')
            kind = s.kind if hasattr(s, 'kind') else s.get('kind', '')
            score = 0
            nl = name.lower()
            if nl == ql: score = 3
            elif nl.startswith(ql): score = 2
            elif ql in nl: score = 1
            if score > 0:
                results.append({'name': name, 'file': file, 'kind': kind, 'score': score, 'repo': str(db_path.parent.parent)})
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:50]
    except Exception:
        return []


def search_all_repos(query: str, repo_dirs: list[str] | None = None) -> list[dict]:
    """Search all registered repos in parallel. Returns merged+ranked results."""
    if repo_dirs is None:
        from rekipedia.watcher.watcher import list_repos
        repo_dirs = list_repos()
    
    db_paths = []
    for repo in repo_dirs:
        db = Path(repo) / '.rekipedia' / 'rekipedia.db'
        if db.exists():
            db_paths.append(db)
    
    if not db_paths:
        return []
    
    all_results = []
    with ThreadPoolExecutor(max_workers=min(len(db_paths), 8)) as pool:
        futures = {pool.submit(_search_single_repo, db, query): db for db in db_paths}
        for fut in as_completed(futures):
            all_results.extend(fut.result())
    
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:200]
