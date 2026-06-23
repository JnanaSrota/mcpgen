[![CI](https://github.com/JnanaSrota/mcpgen/actions/workflows/ci.yml/badge.svg)](https://github.com/JnanaSrota/mcpgen/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mcgen.svg)](https://pypi.org/project/mcgen/)
[![Python versions](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

# mcgen

> Turn any API into an MCP server in 30 seconds.

[![asciicast](https://asciinema.org/a/zCiwFOtTHQzIrTpU.svg)](https://asciinema.org/a/zCiwFOtTHQzIrTpU)

[![PyPI version](https://badge.fury.io/py/mcgen.svg)](https://pypi.org/project/mcgen/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Point mcgen at an OpenAPI spec or Postman collection. Get back a complete, **source-code MCP server you own** — no runtime dependency on mcgen, no black box, no lock-in. Read it. Modify it. Ship it.

---

## Install

```bash
pip install mcgen
```

## Quickstart

```bash
# From a URL
mcgen https://petstore3.swagger.io/api/v3/openapi.json

# From a local file
mcgen stripe.yaml

# Preview without writing anything
mcgen openapi.json --dry-run

# Custom output directory
mcgen openapi.json --output ~/my-mcp-servers

# Control the output name
mcgen https://petstore3.swagger.io/api/v3/openapi.json --name "Petstore"
```

That's it. mcgen reads your spec and writes a Python MCP server to disk.

## What you get

A self-contained directory you can read, edit, and deploy anywhere:

```
stripe_api_mcp/
├── server.py          ← the MCP server (yours to customize)
└── requirements.txt   ← httpx, mcp
```

Run it immediately:

```bash
cd stripe_api_mcp
pip install -r requirements.txt
export STRIPE_API_TOKEN="sk_live_..."
python server.py
```

## Add to Claude Desktop

mcgen prints the exact config block to paste into `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stripe-api-mcp": {
      "command": "python",
      "args": ["/path/to/stripe_api_mcp/server.py"],
      "env": { "STRIPE_API_TOKEN": "your-key-here" }
    }
  }
}
```
