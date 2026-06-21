"""Git history extraction and population utilities for rekipedia."""
from __future__ import annotations

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("rekipedia.git_history")


def extract_git_history(repo_root: Path, run_id: str, limit: int = 100) -> list[dict]:
    """Extract the last `limit` git commits and their modified file stats from git repository."""
    commits = []

    # Check if git repository
    if not (repo_root / ".git").exists():
        logger.warning(f"{repo_root} is not a git repository.")
        return []

    try:
        # Run git log to get basic commit details
        log_cmd = ["git", "log", "--pretty=format:%H|%an|%ae|%aI|%s", "-n", str(limit)]
        res = subprocess.run(log_cmd, capture_output=True, text=True, check=True, cwd=str(repo_root), timeout=30)

        lines = res.stdout.splitlines()
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            commit_hash, author_name, author_email, commit_date, message = parts

            # Fetch numstat for this commit
            num_cmd = ["git", "show", "--numstat", "--pretty=", commit_hash]
            num_res = subprocess.run(num_cmd, capture_output=True, text=True, check=True, cwd=str(repo_root), timeout=15)

            file_changes = []
            for num_line in num_res.stdout.splitlines():
                num_line = num_line.strip()
                if not num_line:
                    continue
                num_parts = num_line.split("\t", 2)
                if len(num_parts) < 3:
                    continue
                add_str, del_str, file_path = num_parts

                try:
                    additions = int(add_str) if add_str != "-" else 0
                    deletions = int(del_str) if del_str != "-" else 0
                except ValueError:
                    additions, deletions = 0, 0

                file_changes.append({
                    "file_path": file_path,
                    "additions": additions,
                    "deletions": deletions
                })

            commits.append({
                "commit_hash": commit_hash,
                "author_name": author_name,
                "author_email": author_email,
                "commit_date": commit_date,
                "message": message,
                "file_changes": file_changes
            })

    except Exception as e:
        logger.error(f"Failed to extract git history from {repo_root}: {e}")
        return []

    return commits


def save_git_history(store, run_id: str, commits: list[dict]) -> None:
    """Save git history to SQLite database."""
    conn = store._conn
    if not conn:
        raise RuntimeError("SqliteStore must be opened as a context manager first")

    for c in commits:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO git_commits (commit_hash, run_id, author_name, author_email, commit_date, message) VALUES (?, ?, ?, ?, ?, ?)",
                (c["commit_hash"], run_id, c["author_name"], c["author_email"], c["commit_date"], c["message"])
            )
            for f in c["file_changes"]:
                conn.execute(
                    "INSERT OR REPLACE INTO git_file_changes (commit_hash, run_id, file_path, additions, deletions) VALUES (?, ?, ?, ?, ?)",
                    (c["commit_hash"], run_id, f["file_path"], f["additions"], f["deletions"])
                )
        except Exception as e:
            logger.error(f"Failed to save git commit {c['commit_hash']} to database: {e}")

    conn.commit()


def get_file_commit_counts(store, run_id: str | None = None) -> dict[str, int]:
    """Retrieve the commit counts per file_path."""
    conn = store._conn
    if not conn:
        return {}
    try:
        if run_id:
            rows = conn.execute(
                "SELECT file_path, COUNT(DISTINCT commit_hash) FROM git_file_changes WHERE run_id = ? GROUP BY file_path",
                (run_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT file_path, COUNT(DISTINCT commit_hash) FROM git_file_changes GROUP BY file_path"
            ).fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}
