"""regplan CLI — thin shell, zero business logic."""
from __future__ import annotations

import typer

app = typer.Typer(name="regplan", help="Regulatory compliance planning tool.")


@app.command()
def validate(
    landscape: typer.FileText = typer.Argument(..., help="Path to landscape YAML"),
) -> None:
    """Validate a landscape YAML file."""
    typer.echo("validate: not yet implemented", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
