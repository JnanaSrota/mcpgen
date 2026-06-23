"""Tests for the Python code generator."""

import pytest
from pathlib import Path
import tempfile

from mcpify.ir import MCPSpec, Tool, Param
from mcpify.generator.python import generate_python, generate_dry_run


def make_simple_spec() -> MCPSpec:
    return MCPSpec(
        name="Test API",
        description="A test API",
        base_url="https://api.test.com",
        tools=[
            Tool(
                name="get_users",
                description="List all users",
                method="GET",
                path="/users",
                params=[
                    Param(name="page", location="query", required=False, type="integer"),
                    Param(name="limit", location="query", required=False, type="integer"),
                ],
                base_url="https://api.test.com",
                auth_type="bearer",
            )
        ],
        auth_type="bearer",
        auth_env_var="TEST_API_TOKEN",
    )


def test_dry_run_returns_string():
    spec = make_simple_spec()
    code = generate_dry_run(spec)
    assert isinstance(code, str)
    assert len(code) > 0


def test_generated_code_has_tool_name():
    spec = make_simple_spec()
    code = generate_dry_run(spec)
    assert "get_users" in code


def test_generated_code_has_base_url():
    spec = make_simple_spec()
    code = generate_dry_run(spec)
    assert "https://api.test.com" in code


def test_generated_code_has_auth_env_var():
    spec = make_simple_spec()
    code = generate_dry_run(spec)
    assert "TEST_API_TOKEN" in code


def test_generate_writes_files():
    spec = make_simple_spec()
    with tempfile.TemporaryDirectory() as tmpdir:
        created = generate_python(spec, Path(tmpdir))
        assert len(created) == 2
        server_file = next(f for f in created if f.name == "server.py")
        req_file = next(f for f in created if f.name == "requirements.txt")
        assert server_file.exists()
        assert req_file.exists()
        code = server_file.read_text()
        assert "get_users" in code
        assert "mcp" in req_file.read_text()


def test_generate_slug_directory():
    spec = make_simple_spec()
    with tempfile.TemporaryDirectory() as tmpdir:
        created = generate_python(spec, Path(tmpdir))
        # Should be inside test_api_mcp/
        assert "test_api_mcp" in str(created[0])