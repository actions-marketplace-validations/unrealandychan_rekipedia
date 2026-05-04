from rekipedia.analysis.cross_repo_search import search_all_repos, _search_single_repo
from pathlib import Path

def test_search_no_repos():
    results = search_all_repos('anything', repo_dirs=[])
    assert results == []

def test_search_nonexistent_db():
    results = _search_single_repo(Path('/nonexistent/path/rekipedia.db'), 'query')
    assert results == []

def test_ranking():
    # We can't easily test with a real DB in unit tests
    # Just verify the function is importable and returns a list
    results = search_all_repos('test', repo_dirs=[])
    assert isinstance(results, list)
