# CellarTracker CLI

Python CLI for managing a CellarTracker wine cellar using requests + BeautifulSoup for web scraping and Click for the CLI interface.

## Tech Stack

- Python 3.11+
- Poetry for dependency management
- requests - HTTP client
- beautifulsoup4 - HTML parsing
- click - CLI framework
- python-dotenv - Environment variable loading

## How to Run

```bash
poetry install
ct <command>
```

The `ct` command is installed as a console script entry point via Poetry.

## Architecture

- `cellartracker/client.py` - HTTP client and HTML parsing. `CellarTrackerClient` handles authentication (cookie-based via POST to `/classic/password.asp`) and all CellarTracker interactions. Dataclasses: `WineResult`, `TastingNote`, `Bottle`.
- `cellartracker/cli.py` - Click CLI commands: `login`, `search`, `add`, `add-pending`, `cellar`, `pending`, `notes`, `bottles`. Entry point: `cli()` function.

## Maintenance

- When adding or modifying features, update `SKILL.md` to keep it in sync with the CLI capabilities.

## Key Conventions

- Auth via `.env` file (`CELLARTRACKER_USER`, `CELLARTRACKER_PASSWORD`)
- Cookie-based auth: `User` + `PWHash` cookies from POST to `/classic/password.asp`
- HTML parsing with BeautifulSoup using CSS class selectors (`el nam`, `el loc`, `el var`, `el gty`, `el scr`)
- Tasting notes parsed from `notes.asp?iWine=<id>` using `ul.comments` structure (author from `span.static`, score from `span.score`, text from `p.break_word`)
- Individual bottles parsed from `list.asp?Table=Inventory&iWine=<id>` (location from `el loc`, store from `el str`, size from `el siz`, price from `el prc`, date from `el dat`)
- Form submissions to `purchase.asp` for adding/editing wines
- Default currency is USD (override with `--currency` flag)

## Security

- Never commit `.env` - it contains credentials
- Never hardcode credentials in source files
- `.gitignore` excludes `.env`, `.venv/`, `__pycache__/`

## Testing

```bash
ct login              # Verify auth works
ct search "test"      # Verify search works
ct notes <wine_id>    # View community tasting notes (use -n to limit)
ct bottles <wine_id>  # View individual bottles for a wine
```
