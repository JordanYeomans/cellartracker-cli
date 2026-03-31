"""CellarTracker CLI - manage your wine cellar from the command line."""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from cellartracker.client import CellarTrackerClient

# Load .env from the package's project root so `ct` works from any directory
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")
load_dotenv()  # Also check cwd as fallback


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
@click.option("--cost", default=None, help="Cost per bottle (required unless --free)")
@click.option("--currency", default="AUD", help="Currency code (default: AUD)")
@click.option("--free", is_flag=True, help="Explicitly mark as free/gifted ($0 cost)")
def add(wine_id: int, quantity: int, size: str, location: str, bin_loc: str,
        note: str, store: str, cost: str, currency: str, free: bool):
    """Add a wine to your cellar. Use wine ID from search results.

    Cost is required. Use --free for bottles that were genuinely free/gifted.
    """
    if cost is None and not free:
        raise click.UsageError(
            "Cost per bottle is required. Use --cost AMOUNT or --free if it was genuinely free/gifted."
        )
    cost_value = "0" if free else cost

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
        cost=cost_value,
        currency=currency,
    )

    if success:
        click.echo(f"Added {quantity}x wine {wine_id} to cellar")
    else:
        click.echo("Failed to add wine", err=True)
        sys.exit(1)


@cli.group(invoke_without_command=True)
@click.pass_context
def pending(ctx):
    """List wines pending delivery, or use 'pending add' to add one."""
    if ctx.invoked_subcommand is not None:
        return

    client = get_client()
    results = client.get_pending()

    if not results:
        click.echo("No wines pending delivery.")
        return

    click.echo(f"Pending ({len(results)} wines):\n")
    for wine in results:
        click.echo(f"  {wine.display()}")


@pending.command("add")
@click.argument("wine_id", type=int)
@click.option("--quantity", "-q", default=1, help="Number of bottles")
@click.option("--size", "-s", default="750ml", help="Bottle size")
@click.option("--note", "-n", default="", help="Bottle note")
@click.option("--store", default="", help="Store name")
@click.option("--cost", default=None, help="Cost per bottle (required unless --free)")
@click.option("--currency", default="AUD", help="Currency code (default: AUD)")
@click.option("--free", is_flag=True, help="Explicitly mark as free/gifted ($0 cost)")
def pending_add(wine_id: int, quantity: int, size: str, note: str,
                store: str, cost: str, currency: str, free: bool):
    """Add a wine as pending delivery. Use wine ID from search results.

    Cost is required. Use --free for bottles that were genuinely free/gifted.
    """
    if cost is None and not free:
        raise click.UsageError(
            "Cost per bottle is required. Use --cost AMOUNT or --free if it was genuinely free/gifted."
        )
    cost_value = "0" if free else cost

    client = get_client()
    success = client.add_wine(
        wine_id=wine_id,
        quantity=quantity,
        size=size,
        pending=True,
        bottle_note=note,
        store=store,
        cost=cost_value,
        currency=currency,
    )

    if success:
        click.echo(f"Added {quantity}x wine {wine_id} as pending delivery")
    else:
        click.echo("Failed to add wine", err=True)
        sys.exit(1)


@cli.command()
@click.option("--live", is_flag=True, help="Bypass cache: query live data for each wine (slower but accurate)")
@click.option("--filter", "-f", "filter_text", default="", help="Filter results by name (case-insensitive)")
def cellar(live: bool, filter_text: str):
    """List wines in your cellar."""
    client = get_client()

    if live:
        # Use inmycellar.asp per-wine for live counts (bypasses CT cache)
        click.echo("Fetching live data (bypassing cache)...")
        cached = client.get_my_cellar()
        # Filter first to avoid hammering the API for all 200 wines
        if filter_text:
            cached = [w for w in cached if filter_text.lower() in w.name.lower()]
        results = []
        for wine in cached:
            _, total, _ = client.get_bottles(wine.wine_id)
            # Rebuild display with live bottle count
            wine.bottles = str(total)
            results.append(wine)
    else:
        results = client.get_my_cellar()
        if filter_text:
            results = [w for w in results if filter_text.lower() in w.name.lower()]

    if not results:
        click.echo("No wines in cellar (or failed to parse).")
        return

    click.echo(f"Cellar ({len(results)} wines):\n")
    for wine in results:
        click.echo(f"  {wine.display()}")


@cli.command()
@click.argument("wine_id", type=int)
@click.option("--rating", "-r", default=None, type=int, help="Your score out of 100")
@click.option("--note", "-n", default="", help="Tasting note or consumption note")
@click.option("--date", "drink_date", default=None, help="Date consumed (MM/DD/YYYY, default: today)")
@click.option("--type", "consumption_type", default=1, type=int,
              help="Consumption type: 1=Drank(default) 2=Gift 3=Restaurant 4=Sold 6=Tasted 7=Broken 9=Missing")
def consume(wine_id: int, rating: int | None, note: str, drink_date: str | None, consumption_type: int):
    """Mark a bottle as consumed. Optionally add a rating and tasting note.

    Use wine ID from search results. Consumes 1 bottle of the specified wine.

    Examples:

      ct consume 1951129 --rating 93 --note "Delicious with steak!"

      ct consume 1951129 --rating 91

      ct consume 1951129 --date 03/28/2026 --note "Great with lamb"
    """
    client = get_client()
    success = client.consume_wine(
        wine_id=wine_id,
        rating=rating,
        note=note,
        drink_date=drink_date,
        consumption_type=consumption_type,
    )
    if success:
        parts = [f"Consumed wine {wine_id}"]
        if rating is not None:
            parts.append(f"rated {rating}/100")
        if note:
            parts.append(f'note: "{note}"')
        click.echo(" · ".join(parts))
    else:
        click.echo("Failed to record consumption", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("wine_id", type=int)
@click.option("--location", "-l", default="Cellar", help="Storage location (must match existing CT location)")
@click.option("--date", "delivery_date", default=None, help="Delivery date DD/MM/YYYY (default: today)")
@click.option("--purchase-id", default=None, help="iPurchase ID (auto-detected if omitted)")
def deliver(wine_id: int, location: str, delivery_date: str | None, purchase_id: str | None):
    """Mark a pending wine as delivered and move it into your cellar.

    Use wine ID from search results. Looks up the pending purchase automatically.

    Examples:

      ct deliver 2353280 --location "WineArk - FortitudeValley"

      ct deliver 4203773 --location "Wine Ark Coburg"

      ct deliver 1234567
    """
    client = get_client()
    try:
        success = client.deliver_pending(
            wine_id=wine_id,
            purchase_id=purchase_id,
            location=location,
            delivery_date=delivery_date,
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if success:
        click.echo(f"Delivered wine {wine_id} → {location}")
    else:
        click.echo("Failed to deliver wine — check wine ID and location name", err=True)
        raise SystemExit(1)


@pending.command("delete")
@click.argument("wine_id", type=int)
@click.option("--purchase-id", default=None, help="iPurchase ID (auto-detected if omitted)")
def pending_delete(wine_id: int, purchase_id: str | None):
    """Delete a pending wine purchase entry.

    Use when you've added a duplicate or want to remove an order from pending.

    Example:

      ct pending delete 5585596
    """
    client = get_client()
    try:
        success = client.delete_pending(wine_id=wine_id, purchase_id=purchase_id)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if success:
        click.echo(f"Deleted pending entry for wine {wine_id}")
    else:
        click.echo("Failed to delete pending entry", err=True)
        raise SystemExit(1)


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


@cli.command()
@click.argument("wine_id", type=int)
def bottles(wine_id: int):
    """Show individual bottles for a wine in your cellar, grouped by purchase."""
    client = get_client()
    wine_name, total, groups = client.get_bottles(wine_id)

    if wine_name:
        click.echo(f"{wine_name}")

    if not groups:
        click.echo("No bottles found.")
        return

    click.echo(f"{total} bottle(s) across {len(groups)} purchase(s):\n")
    for group in groups:
        click.echo(f"  {group.display()}")
        click.echo()


if __name__ == "__main__":
    cli()
