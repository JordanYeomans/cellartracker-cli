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

# Add wine to cellar (--cost is REQUIRED; default currency is AUD)
ct add WINE_ID --quantity N --cost PRICE --currency AUD --store "Store" --location "Cellar" --bin "A1" --note "Note"

# Add a genuinely free/gifted bottle (explicitly $0)
ct add WINE_ID --quantity N --free --store "Store" --note "Free - shipping error"

# View cellar inventory
ct cellar

# View pending deliveries
ct pending

# Add wine as pending delivery (--cost is REQUIRED; default currency is AUD)
ct pending add WINE_ID --quantity N --cost PRICE --currency AUD --store "Store"

# View individual bottles for a wine (location, size, price, store, date)
ct bottles WINE_ID

# View community tasting notes for a wine (default 10, use -n for more)
ct notes WINE_ID
ct notes WINE_ID -n 50
```

## ⚠️ Price Rules (Critical)

**Always confirm the price before adding.** The CLI requires `--cost` on every `add` and `pending add`.

- **Never pass `--cost 0` unless the user explicitly confirms** the wine was free/gifted
- If the price is unknown: **ask Jordan first** — do not add with a guess or zero
- For genuinely free bottles (e.g. shipping errors, gifts), use `--free` flag instead of `--cost 0`
- Default currency is **AUD** — use `--currency USD` etc. only if the purchase was in another currency
- After adding, run `ct bottles WINE_ID` to confirm the price was stored correctly

**Price sources to check (in order):**
1. Order confirmation email (most reliable)
2. Invoice/receipt email or attachment
3. Merchant website (if still listed)
4. Ask Jordan

## Editing Existing Entries

The CLI does not have an edit command. To fix a wrong price or details, use this pattern:

### Find the iPurchase ID
```python
# Run in a Python shell or script
import os, re
from dotenv import load_dotenv
load_dotenv('/home/jy/cellartracker-cli/.env')
from cellartracker.client import CellarTrackerClient

client = CellarTrackerClient(os.environ['CELLARTRACKER_USER'], os.environ['CELLARTRACKER_PASSWORD'])
client.login()

# For cellar entries use inmycellar.asp; for pending use mypending.asp
resp = client.session.get("https://www.cellartracker.com/inmycellar.asp", params={"iWine": WINE_ID})
purchases = re.findall(r"iPurchase=(\d+)", resp.text)
print(purchases)
```

### Delete the bad entry
```python
del_resp = client.session.post("https://www.cellartracker.com/purchase.asp", data={
    "UISource": "editinventory",
    "iWine": WINE_ID,
    "iPurchase": PURCHASE_ID,
    "Action": "Delete",
    "Confirmed": "1",
})
print(del_resp.url)  # Should be editinventory.asp on success
```

### Re-add with correct details
```bash
ct add WINE_ID --quantity N --cost CORRECT_PRICE --currency AUD --store "Store" --location "Location"
# or for pending:
ct pending add WINE_ID --quantity N --cost CORRECT_PRICE --currency AUD --store "Store"
```

### Notes on the CT parser
- `ct bottles` shows `@ USD/bottle` without the amount when currency is USD and the parser doesn't render the exchange rate — this is a **known display bug in the CLI**. The actual data stored in CT is correct. Verify via `inmycellar.asp` directly if in doubt.
- Pending entries use `mypending.asp` not `inmycellar.asp` for iPurchase lookups.

## Workflow

1. Run `ct login` to verify credentials work
2. Run `ct search` to find the wine and get its ID
3. **Confirm the price** — check email, invoice, or ask Jordan
4. Run `ct add` or `ct pending add` with the wine ID and `--cost`
5. Run `ct bottles WINE_ID` to confirm price stored correctly

## Architecture

- `cellartracker/models.py` -- Dataclasses: `WineResult`, `TastingNote`, `BottleInfo`, `PurchaseGroup`.
- `cellartracker/parsers.py` -- HTML parsing functions for CellarTracker pages.
- `cellartracker/client.py` -- `CellarTrackerClient` class handling HTTP auth (cookie-based via `/classic/password.asp`).
- `cellartracker/cli.py` -- Click CLI with seven commands. Entry point: `cellartracker.cli:cli`.

## Key Details

- Auth uses `User` + `PWHash` cookies from POST to `/classic/password.asp`
- Wine search parses HTML table rows with CSS class selectors (`el nam`, `el loc`, `el var`, `el gty`, `el scr`)
- Adding wines POSTs form data to `purchase.asp`
- Default currency is **AUD**; override with `--currency USD` etc.
- `--cost` is required on `add` and `pending add`; use `--free` for genuinely $0 bottles
- Tasting notes parsed from `notes.asp?iWine=<id>` (community notes only, no pro reviews)
- Individual bottles parsed from `list.asp?Table=Inventory&iWine=<id>` (location, store, size, price, date)
- Wine IDs from search output are required for `add`, `pending add`, `notes`, and `bottles` commands
