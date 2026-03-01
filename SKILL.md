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

# Add wine as pending delivery
ct add-pending WINE_ID --quantity N --cost PRICE --store "Store"

# View cellar inventory
ct cellar

# View pending deliveries
ct pending

# View individual bottles for a wine (location, size, price, store, date)
ct bottles WINE_ID

# View community tasting notes for a wine (default 10, use -n for more)
ct notes WINE_ID
ct notes WINE_ID -n 50
```

## Workflow

1. Run `ct login` to verify credentials work
2. Run `ct search` to find the wine and get its ID
3. Run `ct add` or `ct add-pending` with the wine ID
4. Run `ct cellar` or `ct pending` to confirm

## Architecture

- `cellartracker/client.py` -- `CellarTrackerClient` class handling HTTP auth (cookie-based via `/classic/password.asp`) and HTML parsing with BeautifulSoup. Dataclasses: `WineResult`, `TastingNote`, `Bottle`.
- `cellartracker/cli.py` -- Click CLI with eight commands. Entry point: `cellartracker.cli:cli`.

## Key Details

- Auth uses `User` + `PWHash` cookies from POST to `/classic/password.asp`
- Wine search parses HTML table rows with CSS class selectors (`el nam`, `el loc`, `el var`, `el gty`, `el scr`)
- Adding wines POSTs form data to `purchase.asp`
- Default currency is USD; override with `--currency`
- Tasting notes parsed from `notes.asp?iWine=<id>` (community notes only, no pro reviews)
- Individual bottles parsed from `list.asp?Table=Inventory&iWine=<id>` (location, store, size, price, date)
- Wine IDs from search output are required for `add`, `add-pending`, `notes`, and `bottles` commands
