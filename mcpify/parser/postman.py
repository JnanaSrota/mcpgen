"""
Postman Collection v2.1 parser → MCPSpec.

Handles:
- Flat and nested folder structures (recursively flattens)
- Variable substitution for {{baseUrl}}
- Basic auth and API key detection from collection auth

Does NOT handle:
- Pre-request scripts
- Dynamic variables ({{$randomEmail}}, etc.)
- OAuth flows
"""

from __future__ import annotations
import re
from typing import Optional

from mcpify.ir import MCPSpec, Tool, Param


def parse_postman(data: dict) -> MCPSpec:
    """Parse a Postman Collection v2.1 dict into an MCPSpec."""
    
    info = data.get("info", {})
    name = info.get("name", "Postman Collection")
    description = info.get("description", f"{name} MCP Server")
    if isinstance(description, dict):
        description = description.get("content", name)
    
    # Extract variables for substitution (e.g. {{baseUrl}})
    variables: dict[str, str] = {}
    for var in data.get("variable", []):
        if isinstance(var, dict) and var.get("key"):
            variables[var["key"]] = str(var.get("value", ""))
    
    # Detect auth
    collection_auth = data.get("auth", {})
    auth_type, auth_header, auth_env_var = _detect_postman_auth(collection_auth, name)
    
    # Flatten all items (folders → flat list of requests)
    requests = _flatten_items(data.get("item", []))
    
    if not requests:
        raise ValueError("No requests found in Postman collection.")
    
    # Extract base URL from first request
    base_url = _extract_base_url(requests[0], variables)
    
    tools = []
    for req_item in requests:
        tool = _parse_request(req_item, variables, base_url, auth_type, auth_header)
        if tool:
            tools.append(tool)
    
    return MCPSpec(
        name=name,
        description=description,
        base_url=base_url,
        tools=tools,
        auth_type=auth_type,
        auth_env_var=auth_env_var,
    )


def _flatten_items(items: list, prefix: str = "") -> list[dict]:
    """Recursively flatten nested folders into a flat list of request items."""
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if "item" in item:
            # It's a folder — recurse
            folder_name = item.get("name", "")
            result.extend(_flatten_items(item["item"], f"{prefix}{folder_name}/"))
        elif "request" in item:
            # It's a request — include with folder prefix
            result.append({"_folder_prefix": prefix, **item})
    return result


def _parse_request(
    item: dict,
    variables: dict,
    base_url: str,
    auth_type: str,
    auth_header: Optional[str],
) -> Optional[Tool]:
    """Parse one Postman request item into a Tool."""
    
    request = item.get("request", {})
    if not request or not isinstance(request, dict):
        return None
    
    name = item.get("name", "unknown")
    method = request.get("method", "GET").upper()
    
    # Build tool name from request name
    tool_name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    tool_name = f"{method.lower()}_{tool_name}"
    
    description = request.get("description", name)
    if isinstance(description, dict):
        description = description.get("content", name)
    description = str(description)[:200]
    
    # Extract URL
    url_obj = request.get("url", {})
    if isinstance(url_obj, str):
        full_url = _substitute_vars(url_obj, variables)
        path = "/" + "/".join(full_url.replace(base_url, "").lstrip("/").split("/"))
    elif isinstance(url_obj, dict):
        raw = url_obj.get("raw", "")
        raw = _substitute_vars(raw, variables)
        path_parts = url_obj.get("path", [])
        path = "/" + "/".join(str(p) for p in path_parts)
        path = _substitute_vars(path, variables)
        # Convert Postman :param notation to OpenAPI {param} notation
        path = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
    else:
        return None
    
    params: list[Param] = []
    
    # Query params
    if isinstance(url_obj, dict):
        for qp in url_obj.get("query", []):
            if isinstance(qp, dict) and qp.get("key"):
                params.append(Param(
                    name=qp["key"],
                    location="query",
                    required=False,
                    type="string",
                    description=qp.get("description", ""),
                ))
    
    # Path params
    if isinstance(url_obj, dict):
        for pp in url_obj.get("variable", []):
            if isinstance(pp, dict) and pp.get("key"):
                params.append(Param(
                    name=pp["key"],
                    location="path",
                    required=True,
                    type="string",
                    description=pp.get("description", ""),
                ))
    
    # Body params (raw JSON body)
    body = request.get("body", {})
    if isinstance(body, dict) and body.get("mode") == "raw":
        params.append(Param(
            name="body",
            location="body",
            required=True,
            type="object",
            description="Request body (JSON)",
        ))
    
    return Tool(
        name=tool_name,
        description=description,
        method=method,
        path=path,
        params=params,
        base_url=base_url,
        auth_type=auth_type,
        auth_header=auth_header,
    )


def _extract_base_url(request_item: dict, variables: dict) -> str:
    """Extract base URL from the first request."""
    request = request_item.get("request", {})
    url_obj = request.get("url", {})
    
    if isinstance(url_obj, str):
        url = _substitute_vars(url_obj, variables)
    elif isinstance(url_obj, dict):
        raw = url_obj.get("raw", "")
        url = _substitute_vars(raw, variables)
    else:
        return "https://api.example.com"
    
    # Extract scheme + host
    import re
    match = re.match(r"(https?://[^/]+)", url)
    return match.group(1) if match else "https://api.example.com"


def _detect_postman_auth(auth: dict, api_name: str) -> tuple[str, Optional[str], Optional[str]]:
    """Detect auth type from Postman collection auth object."""
    if not auth:
        return "none", None, None
    
    env_prefix = re.sub(r"[^A-Z0-9]+", "_", api_name.upper()).strip("_")
    auth_type = auth.get("type", "noauth")
    
    if auth_type == "bearer":
        return "bearer", "Authorization", f"{env_prefix}_TOKEN"
    elif auth_type == "apikey":
        key_items = {item["key"]: item.get("value") for item in auth.get("apikey", [])}
        header_name = key_items.get("key", "X-API-Key")
        return "api_key", header_name, f"{env_prefix}_API_KEY"
    elif auth_type == "basic":
        return "basic", "Authorization", f"{env_prefix}_CREDENTIALS"
    
    return "none", None, None


def _substitute_vars(text: str, variables: dict) -> str:
    """Replace {{varName}} with the variable value."""
    def replace(match):
        key = match.group(1).strip()
        return variables.get(key, match.group(0))
    return re.sub(r"\{\{([^}]+)\}\}", replace, text)