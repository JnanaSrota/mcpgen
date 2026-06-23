"""
Internal Representation (IR) for mcpify.

Every parser (OpenAPI, Postman, etc.) outputs an MCPSpec.
The generator consumes MCPSpec. Nothing else crosses that boundary.
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, field_validator
import re


class Param(BaseModel):
    """A single parameter for an API tool call."""

    name: str                   # Python-safe identifier, snake_case
    location: Literal["query", "path", "header", "body", "cookie"]
    required: bool = False
    type: str = "string"        # OpenAPI primitive: string, integer, number, boolean, object, array
    description: Optional[str] = None
    default: Optional[str] = None
    enum: Optional[list[str]] = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Ensure name is a valid Python identifier."""
        v = re.sub(r"[^a-zA-Z0-9_]", "_", v)
        if v and v[0].isdigit():
            v = "_" + v
        return v or "param"


class Tool(BaseModel):
    """Represents one MCP tool, derived from one API endpoint."""

    name: str           # snake_case MCP tool name, e.g. get_users_id
    description: str    # Shown to Claude when it decides which tool to call
    method: str         # HTTP method: GET, POST, PUT, DELETE, PATCH
    path: str           # URL path template, e.g. /users/{id}
    params: list[Param] = []
    base_url: str
    auth_type: Literal["bearer", "api_key", "basic", "none"] = "none"
    auth_header: Optional[str] = None   # For api_key auth: the header name e.g. "X-API-Key"
    content_type: str = "application/json"

    @field_validator("method")
    @classmethod
    def uppercase_method(cls, v: str) -> str:
        return v.upper()

    @field_validator("name")
    @classmethod
    def sanitize_tool_name(cls, v: str) -> str:
        # Replace non-alphanumeric with underscore, collapse multiples, strip leading/trailing
        v = re.sub(r"[^a-zA-Z0-9]+", "_", v)
        v = v.strip("_")
        return v.lower() or "unknown_tool"


class MCPSpec(BaseModel):
    """
    The complete specification for one MCP server.
    
    This is what parsers produce and what the generator consumes.
    """

    name: str           # Human-readable name, e.g. "Stripe API"
    description: str    # Server-level description shown to Claude
    base_url: str       # API base URL, e.g. https://api.stripe.com
    tools: list[Tool]
    auth_type: Literal["bearer", "api_key", "basic", "none"] = "none"
    auth_env_var: Optional[str] = None   # e.g. "STRIPE_TOKEN"
    version: str = "0.1.0"

    @property
    def slug(self) -> str:
        """URL/directory-safe name, e.g. 'stripe_api_mcp'."""
        s = re.sub(r"[^a-zA-Z0-9]+", "_", self.name)
        s = s.strip("_").lower()
        return s + "_mcp"

    @property
    def env_prefix(self) -> str:
        """Env var prefix, e.g. 'STRIPE_API'."""
        return re.sub(r"[^A-Z0-9]+", "_", self.name.upper()).strip("_")