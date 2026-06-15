"""Tests for surprises coupling and command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from rekipedia.analysis.surprises import detect_surprises
from rekipedia.cli.surprises import surprises_cmd


def test_detect_surprises_formula():
    symbols = [
        {"name": "AuthService", "file": "src/auth/service.py", "kind": "class"},
        {"name": "BillingRepo", "file": "src/db/billing.py", "kind": "class"},
    ]
    relationships = [
        {"from_": "AuthService", "to": "BillingRepo", "kind": "calls"},
    ]
    
    surprises = detect_surprises(relationships, symbols)
    assert len(surprises) == 1
    assert surprises[0]["from"] == "AuthService"
    assert surprises[0]["to"] == "BillingRepo"
    assert "layer-violation" in surprises[0]["smells"] or "rare-coupling" in surprises[0]["smells"]


def test_surprises_cmd_error_when_no_db(tmp_path):
    runner = CliRunner()
    result = runner.invoke(surprises_cmd, [str(tmp_path)])
    assert "No rekipedia DB" in result.output
    assert result.exit_code != 0
