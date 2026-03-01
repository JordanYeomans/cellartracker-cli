"""CellarTracker CLI - manage your wine cellar from the command line."""

import os
import sys

import click
from dotenv import load_dotenv

from cellartracker.client import CellarTrackerClient

load_dotenv()


def get_client() -> CellarTrackerClient:
    user = os.environ.get("CELLARTRACKER_USER")
    password = os.environ.get("CELLARTRACKER_PASSWORD")
    if not user or not password:
        click.echo("Error: Set CELLARTRACKER_USER and CELLARTRACKER_PASSWORD in .env", err=True)
        sys.exit(1)
    return CellarTrackerClient(user, password)


@click.group()
def cli():
    """CellarTracker CLI - manage your wine cellar."""
    pass


@cli.command()
def login():
    """Test login credentials."""
    client = get_client()
    if client.login():
        click.echo(f"Logged in as {client.username}")
    else:
        click.echo("Login failed - check your credentials", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--cellar", "-c", is_flag=True, help="Search only your cellar instead of all wines")
def search(query: str, cellar: bool):
    """Search for wines by name, producer, or variety. Searches all wines by default."""
    client = get_client()
    results = client.search_wines(query, my_cellar=cellar)

    if not results:
        click.echo("No wines found.")
        return

    scope = "cellar" if cellar else "all wines"
    click.echo(f"Found {len(results)} wine(s) in {scope}:\n")
    for wine in results:
        click.echo(f"  {wine.display()}")


@cli.command()
@click.argument("wine_id", type=int)
@click.option("--quantity", "-q", default=1, help="Number of bottles")
@click.option("--size", "-s", default="750ml", help="Bottle size")
@click.option("--location", "-l", default="Cellar", help="Storage location")
@click.option("--bin", "bin_loc", default="", help="Bin/slot within location")
@click.option("--note", "-n", default="", help="Bottle note")
@click.option("--store", default="", help="Store name")
@click.option("--cost", default="", help="Cost per bottle")
@click.option("--currency", default="USD", help="Currency code")
def add(wine_id: int, quantity: int, size: str, location: str, bin_loc: str,
        note: str, store: str, cost: str, currency: str):
    """Add a wine to your cellar. Use wine ID from search results."""
    client = get_client()
    success = client.add_wine(
        wine_id=wine_id,
        quantity=quantity,
        size=size,
        pending=False,
        location=location,
        bin_location=bin_loc,
        bottle_note=note,
        store=store,
        cost=cost,
        currency=currency,
    )

    if success:
        click.echo(f"Added {quantity}x wine {wine_id} to cellar")
    else:
        click.echo("Failed to add wine", err=True)
        sys.exit(1)


@cli.command()
@click.argument("wine_id", type=int)
@click.option("--quantity", "-q", default=1, help="Number of bottles")
@click.option("--size", "-s", default="750ml", help="Bottle size")
@click.option("--note", "-n", default="", help="Bottle note")
@click.option("--store", default="", help="Store name")
@click.option("--cost", default="", help="Cost per bottle")
@click.option("--currency", default="USD", help="Currency code")
def add_pending(wine_id: int, quantity: int, size: str, note: str,
                store: str, cost: str, currency: str):
    """Add a wine as pending delivery. Use wine ID from search results."""
    client = get_client()
    success = client.add_wine(
        wine_id=wine_id,
        quantity=quantity,
        size=size,
        pending=True,
        bottle_note=note,
        store=store,
        cost=cost,
        currency=currency,
    )

    if success:
        click.echo(f"Added {quantity}x wine {wine_id} as pending delivery")
    else:
        click.echo("Failed to add wine", err=True)
        sys.exit(1)


@cli.command()
def cellar():
    """List wines in your cellar."""
    client = get_client()
    results = client.get_my_cellar()

    if not results:
        click.echo("No wines in cellar (or failed to parse).")
        return

    click.echo(f"Cellar ({len(results)} wines):\n")
    for wine in results:
        click.echo(f"  {wine.display()}")


@cli.command()
def pending():
    """List wines pending delivery."""
    client = get_client()
    results = client.get_pending()

    if not results:
        click.echo("No wines pending delivery.")
        return

    click.echo(f"Pending ({len(results)} wines):\n")
    for wine in results:
        click.echo(f"  {wine.display()}")


@cli.command()
@click.argument("wine_id", type=int)
@click.option("--limit", "-n", default=10, help="Number of notes to show")
def notes(wine_id: int, limit: int):
    """Show community tasting notes for a wine. Use wine ID from search results."""
    client = get_client()
    wine_name, avg_score, tasting_notes = client.get_tasting_notes(wine_id)

    if wine_name:
        click.echo(f"{wine_name}")
    if avg_score:
        click.echo(f"Average Score: {avg_score}")

    if not tasting_notes:
        click.echo("No tasting notes found.")
        return

    click.echo(f"\nCommunity Notes ({len(tasting_notes)} total):\n")
    for note in tasting_notes[:limit]:
        click.echo(f"  {note.display()}")
        click.echo()


if __name__ == "__main__":
    cli()
