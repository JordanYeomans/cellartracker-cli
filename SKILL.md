---
name: cellartracker
description: "Manage a CellarTracker wine cellar via CLI. Use when: user wants to search wines, add bottles to their cellar, track pending wine deliveries, view cellar inventory, view individual bottles, read tasting notes, or interact with CellarTracker in any way."
metadata: {"openclaw": {"emoji": "🍷", "requires": {"bins": ["python3", "poetry"]}, "install": [{"id": "poetry", "kind": "shell", "command": "pip install poetry", "bins": ["poetry"], "label": "Install Poetry"}]}}
---

# CellarTracker CLI

Manage a CellarTracker wine cellar from the terminal using the `ct` command.

## Setup

```bash
cd {baseDir}/../
poetry install
cp .env.example .env
# Edit .env with CELLARTRACKER_USER and CELLARTRACKER_PASSWORD
```

`poetry install` registers `ct` as a console script. Auth requires a valid CellarTracker account. Credentials are read from `.env` via `python-dotenv`.

## Commands

```bash
# Verify credentials
ct login

# Search all wines (returns wine IDs for use with add/notes)
ct search "QUERY"

# Search only your cellar
ct search "QUERY" --cellar

# Add wine to cellar
ct add WINE_ID --quantity N --cost PRICE --currency USD --store "Store" --location "Cellar" --bin "A1" --note "Note"

# View cellar inventory
ct cellar

# View pending deliveries
ct pending

# Add wine as pending delivery
ct pending add WINE_ID --quantity N --cost PRICE --store "Store"

# View individual bottles for a wine (shows purchase/bottle IDs)
ct bottles WINE_ID

# Edit a purchase (change store, cost, location, date)
ct edit WINE_ID PURCHASE_ID --store "New Store" --cost "25" --location "Cellar"

# Delete an entire purchase (all its bottles)
ct delete WINE_ID PURCHASE_ID

# Consume/drink a bottle (defaults to first available)
ct drink WINE_ID
ct drink WINE_ID --bottle INVENTORY_ID --date "03/01/2026" --note "Great wine"

# Accept delivery of a pending purchase
ct deliver WINE_ID PURCHASE_ID

# View community tasting notes for a wine (default 10, use -n for more)
ct notes WINE_ID
ct notes WINE_ID -n 50
```

## Workflow

1. Run `ct login` to verify credentials work
2. Run `ct search` to find the wine and get its ID
3. Run `ct add` or `ct pending add` with the wine ID
4. Run `ct cellar` or `ct pending` to confirm
5. Run `ct bottles WINE_ID` to see purchase/bottle IDs for edit/delete/drink/deliver
6. Run `ct edit`, `ct delete`, `ct drink`, or `ct deliver` with the appropriate IDs

## Architecture

- `cellartracker/models.py` -- Dataclasses: `WineResult`, `TastingNote`, `BottleInfo`, `PurchaseGroup`.
- `cellartracker/parsers.py` -- HTML parsing functions for CellarTracker pages.
- `cellartracker/client.py` -- `CellarTrackerClient` class handling HTTP auth (cookie-based via `/classic/password.asp`).
- `cellartracker/cli.py` -- Click CLI with eleven commands. Entry point: `cellartracker.cli:cli`.

## Key Details

- Auth uses `User` + `PWHash` cookies from POST to `/classic/password.asp`
- Wine search parses HTML table rows with CSS class selectors (`el nam`, `el loc`, `el var`, `el gty`, `el scr`)
- Adding/editing/deleting wines POSTs form data to `purchase.asp` (Action: Add/Edit/Delete)
- Consuming bottles POSTs to `barcode.asp` with `Choice=dbDrink`
- Accepting deliveries GETs `purchase.asp` with `DeliveryState=delivered`
- Default currency is USD; override with `--currency`
- Tasting notes parsed from `notes.asp?iWine=<id>` (community notes only, no pro reviews)
- Individual bottles parsed from `list.asp?Table=Inventory&iWine=<id>` (location, store, size, price, date)
- Wine IDs from search output are required for `add`, `pending add`, `notes`, and `bottles` commands
