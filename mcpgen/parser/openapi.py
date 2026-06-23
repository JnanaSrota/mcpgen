"""
OpenAPI 3.x parser → MCPSpec (Internal Representation).

Handles:
- Paths and operations (GET/POST/PUT/DELETE/PATCH)
- Parameters (path, query, header, cookie)
- Request bodies (application/json schema properties → body params)
- Security schemes (bearer, apiKey, basic)
- $ref resolution for inline schemas (one level deep)

Does NOT handle:
- Recursive $ref resolution (too complex for MVP, mark as TODO)
- allOf/oneOf/anyOf schema composition
- OAuth flows (marks as "bearer" approximation)
"""

from __future__ import annotations
import re
from typing import Any, Optional
from urllib.parse import urljoin
from mcpgen.ir import MCPSpec, Tool, Param


# Mapping from OpenAPI primitive types to Python type hints
OPENAPI_TO_PYTHON_TYPE: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "object": "dict",
    "array": "list",
}


class OpenAPIParserError(Exception):
    pass


def parse_openapi(data: dict, source_url:str | None = None) -> MCPSpec:
    """Parse an OpenAPI 3.x spec dict into an MCPSpec."""
    
    info = data.get("info", {})
    name = info.get("title", "API")
    description = info.get("description", f"{name} MCP Server")
    
    # Extract base URL from servers array
    servers = data.get("servers", [])
    raw_url = servers[0].get("url", "https://api.example.com") if servers else "https://api.example.com"

# Resolve relative URLs
    if source_url and not raw_url.startswith(("http://", "https://")):
        base_url = urljoin(source_url, raw_url)
    elif not raw_url.startswith(("http://", "https://")):
    # No source URL, use a default base
       base_url = urljoin("https://api.example.com", raw_url)
    else:
       base_url = raw_url

# Strip trailing slash
    base_url = base_url.rstrip("/")
    
    # Detect global auth
    components = data.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    global_security = data.get("security", [])
    
    auth_type, auth_header, auth_env_var = _detect_auth(
        security_schemes, global_security, name
    )
    
    # Parse all paths → tools
    paths = data.get("paths", {})
    tools: list[Tool] = []
    
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]
    
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        
        # Path-level parameters (shared across all operations on this path)
        path_level_params = path_item.get("parameters", [])
        
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue
            
            # Skip deprecated operations
            if operation.get("deprecated", False):
                continue
            
            tool = _parse_operation(
                path=path,
                method=method.upper(),
                operation=operation,
                path_level_params=path_level_params,
                base_url=base_url,
                global_auth_type=auth_type,
                global_auth_header=auth_header,
                components=components,
            )
            tools.append(tool)
    
    if not tools:
        raise OpenAPIParserError(
            "No operations found in the OpenAPI spec. "
            "Make sure the spec has a 'paths' section with at least one operation."
        )
    
    return MCPSpec(
        name=name,
        description=description,
        base_url=base_url,
        tools=tools,
        auth_type=auth_type,
        auth_env_var=auth_env_var,
        version=info.get("version", "0.1.0"),
    )


def _detect_auth(
    security_schemes: dict,
    global_security: list,
    api_name: str,
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Returns (auth_type, auth_header_name, env_var_name).
    auth_type is one of: "bearer", "api_key", "basic", "none"
    """
    if not security_schemes:
        return "none", None, None
    
    # Prefer the first scheme referenced in global security
    active_scheme_name = None
    if global_security:
        for sec_req in global_security:
            if isinstance(sec_req, dict) and sec_req:
                active_scheme_name = next(iter(sec_req.keys()))
                break
    
    # Fall back to first defined scheme
    if not active_scheme_name and security_schemes:
        active_scheme_name = next(iter(security_schemes.keys()))
    
    if not active_scheme_name:
        return "none", None, None
    
    scheme = security_schemes.get(active_scheme_name, {})
    scheme_type = scheme.get("type", "").lower()
    
    env_prefix = re.sub(r"[^A-Z0-9]+", "_", api_name.upper()).strip("_")
    
    if scheme_type == "http":
        http_scheme = scheme.get("scheme", "").lower()
        if http_scheme == "bearer":
            return "bearer", "Authorization", f"{env_prefix}_TOKEN"
        elif http_scheme == "basic":
            return "basic", "Authorization", f"{env_prefix}_CREDENTIALS"
    
    elif scheme_type == "apikey":
        header_name = scheme.get("name", "X-API-Key")
        location = scheme.get("in", "header")
        if location == "header":
            return "api_key", header_name, f"{env_prefix}_API_KEY"
    
    elif scheme_type == "oauth2":
        # Approximate OAuth2 as bearer — user provides their own token
        return "bearer", "Authorization", f"{env_prefix}_TOKEN"
    
    return "none", None, None


def _parse_operation(
    path: str,
    method: str,
    operation: dict,
    path_level_params: list,
    base_url: str,
    global_auth_type: str,
    global_auth_header: Optional[str],
    components: dict,
) -> Tool:
    """Convert one OpenAPI operation into one Tool."""
    
    # Generate tool name from operationId or method+path
    operation_id = operation.get("operationId")
    if operation_id:
        # Convert camelCase to snake_case
        tool_name = _camel_to_snake(operation_id)
    else:
        # Build from method and path: GET /users/{id} → get_users_id
        clean_path = re.sub(r"[{}]", "", path)          # remove braces
        clean_path = re.sub(r"[^a-zA-Z0-9/]", "_", clean_path)  # non-alnum → _
        clean_path = re.sub(r"/+", "_", clean_path)     # slashes → _
        tool_name = f"{method.lower()}_{clean_path}"
    
    # Clean up the tool name
    tool_name = re.sub(r"_+", "_", tool_name).strip("_").lower()
    
    # Description: prefer operation summary, then description, then fallback
    description = (
        operation.get("summary")
        or operation.get("description")
        or f"{method} {path}"
    )
    # Truncate to 200 chars (MCP tool description limit)
    description = description[:200]
    
    # Merge path-level params with operation-level params
    # Operation-level overrides path-level for same name+location
    all_raw_params = list(path_level_params) + list(operation.get("parameters", []))
    
    # Deduplicate: operation-level params win
    seen: dict[tuple, dict] = {}
    for p in all_raw_params:
        key = (p.get("name"), p.get("in"))
        seen[key] = p
    
    params: list[Param] = []
    
    for raw_param in seen.values():
        # Resolve $ref if present
        raw_param = _resolve_ref(raw_param, components)
        param = _parse_parameter(raw_param)
        if param:
            params.append(param)
    
    # Parse requestBody → body params
    request_body = operation.get("requestBody", {})
    if request_body:
        request_body = _resolve_ref(request_body, components)
        body_params = _parse_request_body(request_body, components)
        params.extend(body_params)
    
    # Sort: required params first, then by name
    params.sort(key=lambda p: (not p.required, p.name))
    
    # Determine operation-level auth (can be overridden per-operation)
    op_security = operation.get("security")
    if op_security is not None:
        # Empty list means no auth for this operation
        if not op_security:
            auth_type = "none"
            auth_header = None
        else:
            auth_type = global_auth_type
            auth_header = global_auth_header
    else:
        auth_type = global_auth_type
        auth_header = global_auth_header
    
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


def _parse_parameter(raw: dict) -> Optional[Param]:
    """Parse a single OpenAPI parameter dict into a Param."""
    name = raw.get("name")
    location = raw.get("in")
    
    if not name or not location:
        return None
    
    if location not in ("query", "path", "header", "cookie"):
        return None
    
    # Extract schema
    schema = raw.get("schema", {})
    param_type = schema.get("type", "string")
    enum = schema.get("enum")
    default = schema.get("default")
    
    return Param(
        name=name,
        location=location,
        required=raw.get("required", location == "path"),  # path params always required
        type=param_type,
        description=raw.get("description"),
        default=str(default) if default is not None else None,
        enum=[str(e) for e in enum] if enum else None,
    )


def _parse_request_body(request_body: dict, components: dict) -> list[Param]:
    """
    Parse requestBody into a flat list of Params with location="body".
    
    We flatten one level of schema properties. Deep nesting becomes a single
    "body" param of type "object" — the generated code passes it as-is.
    """
    content = request_body.get("content", {})
    
    # Prefer application/json, fall back to first available
    schema = None
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
    elif content:
        first_content = next(iter(content.values()))
        schema = first_content.get("schema", {})
    
    if not schema:
        return []
    
    # Resolve $ref
    schema = _resolve_ref(schema, components)
    
    required_fields: set[str] = set(schema.get("required", []))
    properties: dict = schema.get("properties", {})
    
    if not properties:
        # Treat entire body as one opaque object param
        return [Param(
            name="body",
            location="body",
            required=request_body.get("required", False),
            type="object",
            description="Request body",
        )]
    
    params = []
    for prop_name, prop_schema in properties.items():
        prop_schema = _resolve_ref(prop_schema, components)
        params.append(Param(
            name=prop_name,
            location="body",
            required=prop_name in required_fields,
            type=prop_schema.get("type", "string"),
            description=prop_schema.get("description"),
            enum=[str(e) for e in prop_schema["enum"]] if "enum" in prop_schema else None,
        ))
    
    return params


def _resolve_ref(obj: dict, components: dict) -> dict:
    """
    Resolve a single-level $ref.
    Only handles '#/components/...' references.
    Does NOT recursively resolve nested $refs (TODO for v0.2).
    """
    if "$ref" not in obj:
        return obj
    
    ref = obj["$ref"]
    if not ref.startswith("#/components/"):
        return obj  # External refs not supported
    
    # "#/components/schemas/Pet" → ["schemas", "Pet"]
    parts = ref.lstrip("#/").split("/")
    # parts = ["components", "schemas", "Pet"]
    
    result = components
    for part in parts[1:]:  # skip "components"
        if not isinstance(result, dict):
            return obj
        result = result.get(part, {})
    
    return result if isinstance(result, dict) else obj


def _camel_to_snake(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    # Insert underscore before uppercase letters
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()