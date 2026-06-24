# Contributing to mcpgen

Thanks for taking the time to contribute! mcpgen is a small, focused tool and every PR matters.

## Quick start

```bash
git clone https://github.com/JnanaSrota/mcpgen.git
cd mcpgen
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest  # all 17 should pass
```

## What to work on

These are the open areas most needing help:

- **TypeScript output** (`--lang ts`) — generate a TS/Node MCP server instead of Python
- **Swagger 2.x support** — currently only OpenAPI 3.x is supported
- **`$ref` recursive resolution** — deeply nested `$ref` chains aren't fully resolved yet
- **Auto-detect OpenAPI URL** from well-known paths (`.well-known/openapi.json`)

Check the [open issues](https://github.com/JnanaSrota/mcpgen/issues) for anything tagged `good first issue` or `help wanted`.

## How to submit a PR

1. Fork the repo and create a branch: `git checkout -b feat/your-feature`
2. Make your changes
3. Add or update tests — all 17 must still pass
4. Run the full suite: `pytest`
5. Open a PR with a clear description of what changed and why

## Project structure

```
mcpgen/
├── cli.py              ← entry point (Typer CLI)
├── parser/
│   ├── loader.py       ← fetch + parse OpenAPI/Postman specs
│   ├── openapi.py      ← OpenAPI 3.x → IR
│   └── postman.py      ← Postman v2.1 → IR
├── ir/
│   └── models.py       ← internal representation (Pydantic)
├── generator/
│   └── python.py       ← IR → Python MCP server
└── templates/
    └── python/
        ├── server.py.jinja2
        └── requirements.txt.jinja2
```

## Code style

- Follow existing patterns — no new dependencies without discussion
- Keep functions small and focused
- Type hints on all public functions

## Reporting bugs

Open an issue with the spec file (or URL) that caused the problem and the full error output. A minimal reproduction is always faster to fix.
