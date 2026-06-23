"""
mcpgen CLI — main entry point.

Usage:
  mcpgen openapi.json
  mcpgen https://petstore3.swagger.io/api/v3/openapi.json
  mcpgen postman.json --output ./my-mcp
  mcpgen openapi.yaml --dry-run
"""

from __future__ import annotations
import time
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from mcpgen import __version__
from mcpgen.parser import load, LoaderError
from mcpgen.generator import generate_python, generate_dry_run

app = typer.Typer(
    name="mcpgen",
    help="Turn any API into an MCP server in 30 seconds.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


def _version_callback(value: bool):
    if value:
        rprint(f"mcpgen v{__version__}")
        raise typer.Exit()


@app.command()
def main(
    source: str = typer.Argument(
        ...,
        help="OpenAPI JSON/YAML file path, Postman collection, or URL",
        metavar="INPUT",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory (default: current directory)",
        metavar="DIR",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name", "-n",
        help="Override the generated server name",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print generated code without writing files",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version", "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """
    [bold cyan]mcpgen[/bold cyan] — Turn any API into an MCP server in 30 seconds.

    Examples:
      mcpgen openapi.json
      mcpgen https://petstore3.swagger.io/api/v3/openapi.json
      mcpgen stripe.yaml --output ./stripe-mcp
      mcpgen postman.json --dry-run
    """
    
    if no_color:
        console._color_system = None
    
    # Header
    console.print()
    console.print(Panel(
        f"[bold cyan]mcpgen[/bold cyan] [dim]v{__version__}[/dim]",
        box=box.ROUNDED,
        expand=False,
        border_style="cyan",
    ))
    console.print()
    
    start = time.monotonic()
    
    # Step 1: Parse
    with console.status("[cyan]Parsing[/cyan] " + source + " ..."):
        try:
            spec = load(source)
        except LoaderError as e:
            console.print(f"  [red]✗ Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"  [red]✗ Unexpected error:[/red] {e}")
            raise typer.Exit(1)
    
    console.print(f"  [dim]Parsed[/dim]   {source}")
    
    # Apply name override
    if name:
        spec = spec.model_copy(update={"name": name})
    
    # Step 2: Report what was found
    console.print(f"  [dim]Found[/dim]    [bold]{len(spec.tools)}[/bold] tool{'s' if len(spec.tools) != 1 else ''} → MCP tools")
    
    if spec.auth_type != "none":
        auth_display = {
            "bearer": f"Bearer token  [dim](set [bold]{spec.auth_env_var}[/bold] env var)[/dim]",
            "api_key": f"API Key       [dim](set [bold]{spec.auth_env_var}[/bold] env var)[/dim]",
            "basic": f"Basic Auth    [dim](set [bold]{spec.auth_env_var}[/bold] env var)[/dim]",
        }.get(spec.auth_type, spec.auth_type)
        console.print(f"  [dim]Auth[/dim]     {auth_display}")
    else:
        console.print(f"  [dim]Auth[/dim]     None detected")
    
    # Step 3: Dry run or generate
    if dry_run:
        console.print()
        console.print("[bold]Generated server.py:[/bold]")
        console.print()
        code = generate_dry_run(spec)
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        raise typer.Exit(0)
    
    # Step 4: Write files
    output_dir = output or Path.cwd()
    
    with console.status("[cyan]Writing[/cyan] " + str(output_dir / spec.slug) + " ..."):
        created = generate_python(spec, output_dir)
    
    console.print(f"  [dim]Wrote[/dim]    [bold]{output_dir / spec.slug}/[/bold]")
    
    # Step 5: Summary
    elapsed = time.monotonic() - start
    console.print()
    
    # Tool list (up to 10)
    if spec.tools:
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("", style="dim")
        table.add_column("")
        for tool in spec.tools[:10]:
            table.add_row("→", f"[bold]{tool.name}[/bold]  [dim]{tool.description[:60]}[/dim]")
        if len(spec.tools) > 10:
            table.add_row("", f"[dim]... and {len(spec.tools) - 10} more[/dim]")
        console.print(table)
        console.print()
    
    # Claude Desktop config snippet
    server_path = output_dir / spec.slug / "server.py"
    config_dict = {
        "command": "python",
        "args": [str(server_path)],
    }
    if spec.auth_env_var:
        config_dict["env"] = {spec.auth_env_var: "your-key-here"}
    
    import json
    config_json = json.dumps(
        {spec.slug: config_dict},
        indent=4
    )
    
    console.print(Panel(
        f"[bold]Add to Claude Desktop config:[/bold]\n\n"
        f"[dim]~/Library/Application Support/Claude/claude_desktop_config.json[/dim]\n\n"
        f'[green]{{"mcpServers": {{\n'
        + "\n".join(f"  {line}" for line in config_json.splitlines())
        + "\n}}}[/green]",
        box=box.ROUNDED,
        border_style="green",
        expand=False,
    ))
    
    console.print()
    console.print(
        f"  [bold green]Done[/bold green] in {elapsed:.1f}s  →  "
        f"[dim]cd {spec.slug} && pip install -r requirements.txt && python server.py[/dim]"
    )
    console.print()