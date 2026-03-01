---
name: cellartracker
description: "Manage a CellarTracker wine cellar via CLI. Use when: user wants to search wines, add bottles to their cellar, track pending wine deliveries, view cellar inventory, or interact with CellarTracker in any way."
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

# Search wines (returns wine IDs for use with add)
ct search "QUERY"

# Add wine to cellar
ct add WINE_ID --quantity N --cost PRICE --currency USD --store "Store" --location "Cellar" --bin "A1" --note "Note"

# Add wine as pending delivery
ct add-pending WINE_ID --quantity N --cost PRICE --store "Store"

# View cellar inventory
ct cellar

# View pending deliveries
ct pending
```

## Workflow

1. Run `ct login` to verify credentials work
2. Run `ct search` to find the wine and get its ID
3. Run `ct add` or `ct add-pending` with the wine ID
4. Run `ct cellar` or `ct pending` to confirm

## Architecture

- `cellartracker/client.py` -- `CellarTrackerClient` class handling HTTP auth (cookie-based via `/classic/password.asp`) and HTML parsing with BeautifulSoup. `WineResult` dataclass for results.
- `cellartracker/cli.py` -- Click CLI with six commands. Entry point: `cellartracker.cli:cli`.

## Key Details

- Auth uses `User` + `PWHash` cookies from POST to `/classic/password.asp`
- Wine search parses HTML table rows with CSS class selectors (`el nam`, `el loc`, `el var`, `el gty`, `el scr`)
- Adding wines POSTs form data to `purchase.asp`
- Default currency is USD; override with `--currency`
- Wine IDs from search output are required for `add` and `add-pending` commands
