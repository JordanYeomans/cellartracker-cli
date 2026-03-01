# CellarTracker CLI

A command-line interface for managing your [CellarTracker](https://www.cellartracker.com) wine cellar.

Search wines, add bottles, track pending deliveries, and view your cellar -- all from the terminal.

> **Disclaimer:** This project is not affiliated with, endorsed by, or associated with CellarTracker LLC. It is an independent, unofficial tool that interacts with the CellarTracker website.

---

### Support CellarTracker

CellarTracker is a fantastic service built and maintained by a small team. If you find this CLI useful, please consider [subscribing to CellarTracker](https://www.cellartracker.com/subscribe.asp) to support the platform and help keep it running for the entire wine community.

---

## Features

- **Search** the CellarTracker database for wines by name, producer, or variety
- **Add** wines to your cellar with quantity, cost, location, and notes
- **Track** pending deliveries separately from your cellar
- **View** your cellar and pending wines at a glance

## Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- A [CellarTracker](https://www.cellartracker.com) account

## Installation

```bash
git clone https://github.com/JordanYeomans/cellartracker-cli.git
cd cellartracker-cli
poetry install
```

This installs the `ct` command into the Poetry virtual environment.

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your CellarTracker credentials:

```
CELLARTRACKER_USER=your_handle_here
CELLARTRACKER_PASSWORD=your_password_here
```

## Usage

### Test login

```bash
ct login
```

### Search for wines

```bash
ct search "Penfolds Grange"
```

Output:

```
Found 3 wine(s):

  [12345] 2018 Penfolds Grange - South Australia (Shiraz) 1 bottle
  [12346] 2019 Penfolds Grange - South Australia (Shiraz) 2 bottles
  [12347] 2020 Penfolds Grange - South Australia (Shiraz) 0 bottles
```

### Add a wine to your cellar

Use the wine ID from search results:

```bash
ct add 12345 --quantity 2 --cost 50 --store "Wine Shop"
```

| Option | Short | Description |
|--------|-------|-------------|
| `--quantity` | `-q` | Number of bottles (default: 1) |
| `--size` | `-s` | Bottle size (default: 750ml) |
| `--location` | `-l` | Storage location (default: Cellar) |
| `--bin` | | Bin/slot within location |
| `--note` | `-n` | Bottle note |
| `--store` | | Store name |
| `--cost` | | Cost per bottle |
| `--currency` | | Currency code (default: USD) |

### Add a wine as pending delivery

```bash
ct add-pending 12345 --quantity 6 --cost 30 --store "Online Store"
```

### View your cellar

```bash
ct cellar
```

### View pending deliveries

```bash
ct pending
```

## Typical Workflow

```bash
# 1. Verify your credentials work
ct login

# 2. Search for the wine you want to add
ct search "Chateau Margaux 2015"

# 3. Add it using the wine ID from search results
ct add 67890 --quantity 3 --cost 200 --store "Bordeaux Direct"

# 4. Check your cellar
ct cellar
```

## License

MIT -- see [LICENSE](LICENSE).
