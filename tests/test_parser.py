"""Tests for the OpenAPI parser."""

import json
import pytest
from pathlib import Path
from mcpify.parser.openapi import parse_openapi
from mcpify.ir import MCPSpec

PETSTORE_FIXTURE = Path(__file__).parent / "fixtures" / "petstore.json"


def load_petstore() -> dict:
    """Load the Petstore fixture. Download it if missing."""
    if not PETSTORE_FIXTURE.exists():
        import httpx
        resp = httpx.get("https://petstore3.swagger.io/api/v3/openapi.json")
        PETSTORE_FIXTURE.parent.mkdir(exist_ok=True)
        PETSTORE_FIXTURE.write_text(resp.text)
    return json.loads(PETSTORE_FIXTURE.read_text())


def test_parse_openapi_returns_mcp_spec():
    data = load_petstore()
    spec = parse_openapi(data)
    assert isinstance(spec, MCPSpec)


def test_parse_openapi_has_tools():
    data = load_petstore()
    spec = parse_openapi(data)
    assert len(spec.tools) > 0


def test_parse_openapi_tool_names_are_snake_case():
    data = load_petstore()
    spec = parse_openapi(data)
    for tool in spec.tools:
        assert tool.name == tool.name.lower()
        assert " " not in tool.name


def test_parse_openapi_base_url():
    data = load_petstore()
    spec = parse_openapi(data)
    assert spec.base_url.startswith("http")
    assert not spec.base_url.endswith("/")


def test_parse_minimal_spec():
    minimal = {
        "openapi": "3.0.3",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        }
    }
    spec = parse_openapi(minimal)
    assert spec.name == "Test API"
    assert len(spec.tools) == 1
    assert spec.tools[0].method == "GET"
    assert spec.tools[0].path == "/users"


def test_parse_bearer_auth():
    spec_data = {
        "openapi": "3.0.3",
        "info": {"title": "Secured API", "version": "1.0.0"},
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
        "security": [{"bearerAuth": []}],
        "paths": {
            "/data": {
                "get": {
                    "summary": "Get data",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        }
    }
    spec = parse_openapi(spec_data)
    assert spec.auth_type == "bearer"
    assert spec.auth_env_var == "SECURED_API_TOKEN"