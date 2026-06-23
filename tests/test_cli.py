"""Integration tests for the CLI."""

import pytest
from typer.testing import CliRunner
from mcpgen.cli import app
import tempfile
from pathlib import Path
import json

runner = CliRunner()


MINIMAL_OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "Test API", "version": "1.0.0"},
    "servers": [{"url": "https://api.test.com"}],
    "paths": {
        "/items": {
            "get": {
                "summary": "List items",
                "responses": {"200": {"description": "OK"}},
            }
        }
    }
}


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "mcpgen" in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "INPUT" in result.output


def test_basic_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write fixture
        spec_file = Path(tmpdir) / "spec.json"
        spec_file.write_text(json.dumps(MINIMAL_OPENAPI))
        
        result = runner.invoke(app, [str(spec_file), "--output", tmpdir])
        assert result.exit_code == 0
        
        server_file = Path(tmpdir) / "test_api_mcp" / "server.py"
        assert server_file.exists()


def test_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_file = Path(tmpdir) / "spec.json"
        spec_file.write_text(json.dumps(MINIMAL_OPENAPI))
        
        result = runner.invoke(app, [str(spec_file), "--dry-run"])
        assert result.exit_code == 0
        assert "server.py" in result.output or "Generated" in result.output
        # No files written
        assert not (Path(tmpdir) / "test_api_mcp").exists()


def test_invalid_input():
    result = runner.invoke(app, ["nonexistent_file.json"])
    assert result.exit_code != 0