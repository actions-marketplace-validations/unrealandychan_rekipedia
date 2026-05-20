"""Tests for the benchmark evaluation suite (issue #139)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BENCHMARKS_DIR = Path(__file__).parent.parent / "benchmarks"
FIXTURES_DIR = BENCHMARKS_DIR / "fixtures"


def test_baselines_json_valid():
    """baselines.json is valid JSON with the expected top-level structure."""
    baselines_path = BENCHMARKS_DIR / "baselines.json"
    assert baselines_path.exists(), "baselines.json not found"
    data = json.loads(baselines_path.read_text())
    assert "version" in data
    assert "benchmarks" in data
    assert "extraction" in data["benchmarks"]
    assert "performance" in data["benchmarks"]
    assert "python_web_app" in data["benchmarks"]["extraction"]
    assert "typescript_react" in data["benchmarks"]["extraction"]
    assert "thresholds" in data["benchmarks"]["performance"]


def test_fixture_files_exist():
    """All fixture files exist on disk."""
    assert (FIXTURES_DIR / "python_web_app" / "app.py").exists()
    assert (FIXTURES_DIR / "typescript_react" / "App.tsx").exists()


def test_extraction_benchmark_passes():
    """run_extraction_benchmark() reports all_passed=True."""
    sys.path.insert(0, str(BENCHMARKS_DIR.parent))
    from benchmarks.run_extraction import run_extraction_benchmark

    results = run_extraction_benchmark(verbose=False)
    assert results["all_passed"] is True, f"Extraction benchmark failed: {results}"


def test_performance_benchmark_passes():
    """run_performance_benchmark() reports passed=True."""
    from benchmarks.run_extraction import run_performance_benchmark

    result = run_performance_benchmark(verbose=False)
    assert result["passed"] is True, f"Performance benchmark failed: {result}"


def test_script_runs_with_json_flag():
    """run_extraction.py --json exits 0 and produces valid JSON."""
    script = BENCHMARKS_DIR / "run_extraction.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Script exited {proc.returncode}:\n{proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["all_passed"] is True
