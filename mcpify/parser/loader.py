"""
Loader: detects input format and routes to the correct parser.

Accepts:
- File path: .json, .yaml, .yml
- URL: fetches content then detects format

Detects:
- OpenAPI 3.x (has "openapi" key starting with "3.")
- Postman Collection v2.1 (has "info._postman_id" key)
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Union

import httpx
import yaml

from mcpify.ir import MCPSpec
from .openapi import parse_openapi
from .postman import parse_postman


class LoaderError(Exception):
    """Raised when the input cannot be loaded or format is unrecognized."""
    pass


def load(source: str) -> MCPSpec:
    """
    Main entry point. Takes a file path or URL string.
    Returns an MCPSpec ready for code generation.
    
    Raises LoaderError if format is unrecognized or fetch fails.
    """
    raw = _fetch(source)
    data = _parse_raw(raw, source)
    if source.startswith(("http://", "https://")):
        return parse_openapi(data, source_url=source)
    else:
        return parse_openapi(data)


def _fetch(source: str) -> str:
    """Fetch raw text from a file path or HTTP URL."""
    if source.startswith(("http://", "https://")):
        try:
            response = httpx.get(source, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            raise LoaderError(f"Failed to fetch URL: {e}") from e
    
    path = Path(source)
    if not path.exists():
        raise LoaderError(f"File not found: {source}")
    return path.read_text(encoding="utf-8")


def _parse_raw(raw: str, source: str) -> dict:
    """
    Parse raw text into a dict.
    Tries JSON first, then YAML.
    Uses file extension as a hint but always validates.
    """
    src_lower = source.lower()
    
    # Try JSON if extension suggests it OR as default first attempt
    if src_lower.endswith(".json") or not src_lower.endswith((".yaml", ".yml")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    
    # Try YAML
    try:
        result = yaml.safe_load(raw)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass
    
    # Last resort: try JSON again (for YAML files that are actually JSON)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    
    raise LoaderError(
        f"Could not parse '{source}' as JSON or YAML. "
        "Check that the file is a valid OpenAPI spec or Postman collection."
    )


def _route(data: dict) -> MCPSpec:
    """Detect format and route to the correct parser."""
    
    # OpenAPI 3.x detection
    openapi_version = data.get("openapi", "")
    if isinstance(openapi_version, str) and openapi_version.startswith("3."):
        return parse_openapi(data)
    
    # Swagger 2.x detection — give a helpful error
    if "swagger" in data:
        raise LoaderError(
            "Swagger 2.x detected. mcpify currently supports OpenAPI 3.x only. "
            "Convert your spec at https://converter.swagger.io/ and try again."
        )
    
    # Postman Collection v2.1 detection
    info = data.get("info", {})
    if "_postman_id" in info or data.get("item"):
        return parse_postman(data)
    
    raise LoaderError(
        "Unrecognized format. mcpify supports:\n"
        "  - OpenAPI 3.x JSON/YAML\n"
        "  - Postman Collection v2.1\n"
        "Check that your file has the correct structure."
    )