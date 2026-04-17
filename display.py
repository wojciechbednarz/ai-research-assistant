from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from chromadb.api.types import QueryResult

console = Console()


def print_header(text: str) -> None:
    """Section divider with title."""
    console.print(Rule(f"[bold cyan]{text}[/bold cyan]", style="cyan"))


def print_success(text: str) -> None:
    console.print(f"[bold green]✓ {text}[/bold green]")


def print_info(text: str) -> None:
    console.print(f"[cyan]ℹ {text}[/cyan]")


def print_warning(text: str) -> None:
    console.print(f"[bold yellow]⚠ {text}[/bold yellow]")


def print_error(text: str) -> None:
    console.print(f"[bold red]✗ {text}[/bold red]")


def print_panel(text: str, title: str = "", style: str = "cyan") -> None:
    """Boxed content for important output."""
    console.print(Panel(text, title=title, border_style=style))


def print_results(results: QueryResult) -> None:
    if (
        not results["ids"]
        or results["distances"] is None
        or results["documents"] is None
    ):
        print_warning("No results found")
        return

    table = Table(title="Query Results")
    table.add_column("ID", style="cyan")
    table.add_column("Distance", style="magenta")
    table.add_column("Document", style="green", no_wrap=False)

    for id_, dist, doc in zip(
        results["ids"][0], results["distances"][0], results["documents"][0]
    ):
        table.add_row(id_, f"{dist:.4f}", doc[:200])

    console.print(table)
