# mcpgen

> Turn any API into an MCP server in 30 seconds.

[![asciicast](https://asciinema.org/a/r5QCO433SyihhTjx.svg)](https://asciinema.org/a/r5QCO433SyihhTjx)

[![PyPI version](https://badge.fury.io/py/mcpgen.svg)](https://badge.fury.io/py/mcpgen)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Point mcpgen at an OpenAPI spec or Postman collection. Get back a complete, **source-code MCP server you own** — no runtime dependency on mcpgen, no black box, no lock-in. Read it. Modify it. Ship it.

---

## Install

```bash
pip install mcpgen
```

## Quickstart

```bash
# From a URL
mcpgen https://petstore3.swagger.io/api/v3/openapi.json

# From a local file
mcpgen stripe.yaml

# Preview without writing anything
mcpgen openapi.json --dry-run

# Custom output directory
mcpgen openapi.json --output ~/my-mcp-servers

# Control the output name
mcpgen https://petstore3.swagger.io/api/v3/openapi.json --name "Petstore"
```

That's it. mcpgen reads your spec and writes a Python MCP server to disk.

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

mcpgen prints the exact config block to paste into `claude_desktop_config.json`:

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

## Supported inputs

| Format                  | Example                                              |
|-------------------------|------------------------------------------------------|
| OpenAPI 3.x JSON        | `mcpgen openapi.json`                                |
| OpenAPI 3.x YAML        | `mcpgen api.yaml`                                    |
| URL (OpenAPI)           | `mcpgen https://api.example.com/openapi.json`        |
| Postman Collection v2.1 | `mcpgen collection.json`                             |

## Why mcpgen?

Most API-to-MCP tools are **runtime proxies** — your server only works as long as their service does. mcpgen is different:

- **You own the code.** The output is plain Python. Read it, audit it, fork it.
- **No runtime dependency.** mcpgen is only needed to generate. After that, throw it away.
- **Deploy anywhere.** The generated server runs wherever Python runs.
- **Customize freely.** Auth logic, retry behavior, response shaping — it's all in a file you control.

## Tested APIs

- Petstore (`https://petstore3.swagger.io/api/v3/openapi.json`)
- GitHub REST API
- Stripe (subset)
- Any OpenAPI 3.x spec

## Roadmap

Contributions are welcome in these areas:

- [ ] TypeScript output (`--lang ts`)
- [ ] Swagger 2.x support
- [ ] `$ref` recursive resolution
- [ ] Auto-detect OpenAPI URL from well-known paths (`.well-known/openapi.json`)

## Contributing

PRs and issues welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup instructions.

```bash
git clone https://github.com/JnanaSrota/mcpgen
cd mcpgen
pip install -e ".[dev]"
pytest
```

## License

MIT — do whatever you want with mcpgen and with the code it generates.