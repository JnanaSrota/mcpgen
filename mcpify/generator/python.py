"""
Python MCP server generator.

Consumes an MCPSpec (IR) and renders the Jinja2 templates
into a complete, standalone Python MCP server directory.
"""

from __future__ import annotations
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from mcpify.ir import MCPSpec

# Path to templates dir relative to this file
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "python"


def _get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),  # only for .html, not .py
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Custom filter: convert OpenAPI type to Python type hint
    env.filters["python_type"] = _openapi_to_python_type
    return env


def _openapi_to_python_type(openapi_type: str) -> str:
    mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "object": "dict",
        "array": "list",
    }
    return mapping.get(openapi_type, "str")


def generate_python(spec: MCPSpec, output_dir: Path) -> list[Path]:
    """
    Generate a Python MCP server from an MCPSpec.
    
    Creates output_dir/{slug}/ with:
      - server.py
      - requirements.txt
    
    Returns list of created file paths.
    """
    env = _get_jinja_env()
    
    server_dir = output_dir / spec.slug
    server_dir.mkdir(parents=True, exist_ok=True)
    
    created_files: list[Path] = []
    
    # Render server.py
    server_template = env.get_template("server.py.jinja2")
    server_code = server_template.render(spec=spec)
    server_path = server_dir / "server.py"
    server_path.write_text(server_code, encoding="utf-8")
    created_files.append(server_path)
    
    # Render requirements.txt
    req_template = env.get_template("requirements.txt.jinja2")
    req_text = req_template.render(spec=spec)
    req_path = server_dir / "requirements.txt"
    req_path.write_text(req_text, encoding="utf-8")
    created_files.append(req_path)
    
    return created_files


def generate_dry_run(spec: MCPSpec) -> str:
    """Return the generated server.py as a string without writing to disk."""
    env = _get_jinja_env()
    template = env.get_template("server.py.jinja2")
    return template.render(spec=spec)