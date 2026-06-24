# Contributing to mcpgen

Thanks for wanting to contribute. Here's how to get started fast.

## Setup

```bash
git clone https://github.com/JnanaSrota/mcpgen
cd mcpgen
pip install -e ".[dev]"
pytest tests/ -v
```

All tests should pass on a clean clone.

## Architecture

The codebase has three distinct layers. Keep them decoupled.

```
mcpgen/
├── parser/
│   ├── loader.py        ← detects format, routes to correct parser
│   ├── openapi.py       ← OpenAPI 3.x → MCPSpec (IR)
│   └── postman.py       ← Postman Collection v2.1 → MCPSpec (IR)
├── ir/
│   └── models.py        ← MCPSpec, Tool, Param (the internal representation)
├── generator/
│   └── python.py        ← MCPSpec → Python source code via Jinja2
└── templates/
    └── python/
        └── server.py.jinja2
```

**The rule:** parsers only produce `MCPSpec`. The generator only consumes `MCPSpec`. The IR is the contract between them.

## Adding a new input format

1. Create `mcpgen/parser/yourformat.py`
2. Write a `parse_yourformat(data: dict) -> MCPSpec` function
3. Add detection logic in `loader.py`'s `_route()` function
4. Add fixture files in `tests/fixtures/`
5. Add tests in `tests/test_parser.py`

Nothing in the generator needs to change.

## Adding a new output language

1. Create `mcpgen/generator/typescript.py` (or whatever language)
2. Write a `generate_typescript(spec: MCPSpec, output_dir: Path) -> list[Path]` function
3. Create templates in `mcpgen/templates/typescript/`
4. Add `--lang` option handling in `cli.py`

Nothing in the parsers needs to change.

## What makes a good PR

- Tests for new behavior
- Existing tests still pass (`pytest tests/ -v`)
- New parser: include at least one real-world fixture file (OpenAPI spec or Postman collection)
- New output language: include a `test_generator_*.py`

## Issues

Good first issues are labeled `good first issue`. Feature requests and bug reports both welcome — open an issue before starting on a large feature.