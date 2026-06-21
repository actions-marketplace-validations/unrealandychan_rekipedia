-- Migration 008: Git history support for spatio-temporal codebase analysis

CREATE TABLE IF NOT EXISTS git_commits (
    commit_hash TEXT PRIMARY KEY,
    run_id TEXT,
    author_name TEXT,
    author_email TEXT,
    commit_date TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS git_file_changes (
    commit_hash TEXT,
    run_id TEXT,
    file_path TEXT,
    additions INTEGER,
    deletions INTEGER,
    FOREIGN KEY(commit_hash) REFERENCES git_commits(commit_hash)
);

CREATE INDEX IF NOT EXISTS idx_git_file_changes_file_path ON git_file_changes(file_path);
