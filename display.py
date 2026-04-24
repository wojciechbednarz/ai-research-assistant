from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console(stderr=True)


def print_header(text: str) -> None:
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
    console.print(Panel(text, title=title, border_style=style))
