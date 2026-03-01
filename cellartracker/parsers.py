"""HTML parsers for CellarTracker pages."""

import re

from bs4 import BeautifulSoup

from cellartracker.models import (
    BottleInfo,
    PurchaseGroup,
    TastingNote,
    WineResult,
)


def parse_search_results(html: str) -> list[WineResult]:
    """Parse wine search results from HTML.

    HTML structure per row:
      td.bulkedit: checkbox with value=iWine
      td.type: link with wine type text (Red, White, etc.)
      td.name: span.el.nam > h3 (vintage + name), span.el.loc (region), span.el.var (variety)
      td.dates: span.el.gty (quantity)
      td.score: span.el.scr > a (score)
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    table = soup.find("table")
    if not table:
        return results

    rows = table.find_all("tr")
    for row in rows[1:]:  # Skip header
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Wine ID from checkbox or link
        checkbox = row.find("input", {"name": "iWine"})
        if checkbox:
            wine_id = int(checkbox.get("value", 0))
        else:
            link = row.find("a", href=re.compile(r"iWine=\d+"))
            if not link:
                continue
            wine_id = int(re.search(r"iWine=(\d+)", link["href"]).group(1))

        # Wine type
        type_cell = row.find("td", class_="type")
        wine_type = type_cell.get_text(strip=True) if type_cell else ""

        # Name cell with structured spans
        name_cell = row.find("td", class_="name")
        vintage, name, region, variety = "", "", "", ""
        if name_cell:
            # Vintage + Name from h3
            h3 = name_cell.find("h3")
            if h3:
                full_name = h3.get_text(strip=True)
                parts = full_name.split(" ", 1)
                if parts and parts[0].isdigit():
                    vintage = parts[0]
                    name = parts[1] if len(parts) > 1 else ""
                elif full_name.startswith("N.V.") or full_name.startswith("NV"):
                    vintage = "NV"
                    name = full_name.replace("N.V. ", "").replace("NV ", "")
                else:
                    vintage = ""
                    name = full_name

            # Region from span.el.loc
            loc_span = name_cell.find("span", class_="el loc")
            if loc_span:
                region = loc_span.get_text(strip=True)

            # Variety from span.el.var
            var_span = name_cell.find("span", class_="el var")
            if var_span:
                # Remove "more" link text
                more_link = var_span.find("a", class_="more")
                if more_link:
                    more_link.decompose()
                variety = var_span.get_text(strip=True)

        # Quantity: span.el.gty (search) or span.el.num (cellar)
        gty_span = row.find("span", class_="el gty")
        if not gty_span:
            gty_span = row.find("span", class_="el num")
        bottles = gty_span.get_text(strip=True) if gty_span else ""

        # Score from span.el.scr
        scr_span = row.find("span", class_="el scr")
        score = ""
        if scr_span:
            score_link = scr_span.find("a")
            score = score_link.get_text(strip=True) if score_link else scr_span.get_text(strip=True)

        results.append(WineResult(
            wine_id=wine_id,
            vintage=vintage,
            name=name,
            region=region,
            variety=variety,
            wine_type=wine_type,
            bottles=bottles,
            score=score,
        ))

    return results


def parse_cellar_bottles(html: str) -> tuple[str, int, list[PurchaseGroup]]:
    """Parse bottles from inmycellar.asp grouped by purchase.

    HTML structure:
      div.inventory_header > div.copy > h3 (purchase summary), p (cost)
      table.inventory_list (follows each header) > tr rows with columns:
        #, Barcode, Size, Status, Location, Bin, Note
    """
    soup = BeautifulSoup(html, "html.parser")

    # Wine name from page title: "In My Cellar - WINE NAME - CellarTracker"
    wine_name = ""
    title = soup.find("title")
    if title:
        title_text = title.get_text(strip=True)
        match = re.search(r"In My Cellar - (.+?) - CellarTracker", title_text)
        if match:
            wine_name = match.group(1)

    groups = []
    total_bottles = 0
    headers = soup.find_all("div", class_="inventory_header")

    for header in headers:
        copy_div = header.find("div", class_="copy")
        if not copy_div:
            continue

        # Extract iPurchase from edit link in header
        purchase_id = ""
        edit_link = header.find("a", href=re.compile(r"iPurchase=\d+"))
        if edit_link:
            pid_match = re.search(r"iPurchase=(\d+)", edit_link["href"])
            if pid_match:
                purchase_id = pid_match.group(1)

        h3 = copy_div.find("h3")
        p = copy_div.find("p")
        h3_text = h3.get_text(strip=True) if h3 else ""

        # Parse h3: "4 (750ml) purchased from<store> on <date>[, delivered <date>]"
        qty_match = re.match(r"(\d+)\s*\(([^)]+)\)", h3_text)
        quantity = qty_match.group(1) if qty_match else ""
        size = qty_match.group(2) if qty_match else ""

        store = ""
        store_match = re.search(r"from(.+?)\s+on\s+", h3_text)
        if store_match:
            store = store_match.group(1).strip()

        purchase_date = ""
        date_match = re.search(r"\bon\s+(\d+/\d+/\d+)", h3_text)
        if date_match:
            purchase_date = date_match.group(1)

        # Parse cost from p tag
        cost = ""
        if p:
            cost_match = re.search(r"Cost Per Bottle:\s*(\S+)", p.get_text(strip=True))
            if cost_match:
                cost = cost_match.group(1)

        # Parse bottle rows from the following table
        table = header.find_next_sibling("table", class_="inventory_list")
        bottles = []
        if table:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) >= 7:
                    # Extract iInventory from checkbox input
                    inventory_id = ""
                    inv_input = row.find("input", {"name": "iInventory"})
                    if inv_input:
                        inventory_id = inv_input.get("value", "")
                    bottles.append(BottleInfo(
                        number=cells[0].get_text(strip=True),
                        barcode=cells[1].get_text(strip=True),
                        size=cells[2].get_text(strip=True),
                        status=cells[3].get_text(strip=True),
                        location=cells[4].get_text(strip=True),
                        bin=cells[5].get_text(strip=True),
                        note=cells[6].get_text(strip=True),
                        inventory_id=inventory_id,
                    ))

        total_bottles += len(bottles)
        groups.append(PurchaseGroup(
            quantity=quantity,
            size=size,
            store=store,
            purchase_date=purchase_date,
            cost_per_bottle=cost,
            bottles=bottles,
            purchase_id=purchase_id,
        ))

    return wine_name, total_bottles, groups


def parse_pending_bottles(html: str) -> tuple[str, int, list[PurchaseGroup]]:
    """Parse pending purchases from mypending.asp.

    HTML structure:
      h2 (wine name)
      table.storelist > tr rows with columns:
        Purchased/Delivered, Store, Note, #/Left/Size, Price, options
    """
    soup = BeautifulSoup(html, "html.parser")

    wine_name = ""
    h2 = soup.find("h2")
    if h2:
        wine_name = h2.get_text(strip=True)

    groups = []
    total_bottles = 0
    table = soup.find("table", class_="storelist")
    if not table:
        return wine_name, total_bottles, groups

    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        # Extract iPurchase from edit/options links
        purchase_id = ""
        options_link = row.find("a", href=re.compile(r"iPurchase=\d+"))
        if options_link:
            pid_match = re.search(r"iPurchase=(\d+)", options_link["href"])
            if pid_match:
                purchase_id = pid_match.group(1)

        # Purchased/Delivered: "9/09/2025, due" or "9/09/2025, 1/10/2025"
        date_text = cells[0].get_text(strip=True)
        purchase_date = date_text.split(",")[0].strip()

        store = cells[1].get_text(strip=True)
        if store == "n/a":
            store = ""

        # #/Left/Size: "3(1.5L)" or "6,3(750ml)"
        qty_text = cells[3].get_text(strip=True)
        qty_match = re.match(r"(\d+)(?:,(\d+))?\(([^)]+)\)", qty_text)
        quantity = ""
        remaining = ""
        size = ""
        if qty_match:
            quantity = qty_match.group(1)
            remaining = qty_match.group(2) or quantity
            size = qty_match.group(3)

        cost_per_bottle = cells[4].get_text(strip=True)

        total_bottles += int(remaining) if remaining else 0
        groups.append(PurchaseGroup(
            quantity=remaining or quantity,
            size=size,
            store=store,
            purchase_date=purchase_date,
            cost_per_bottle=cost_per_bottle,
            bottles=[BottleInfo(
                number="", barcode="", size=size,
                status="Pending delivery", location="",
                bin="", note="",
            )] * (int(remaining) if remaining else 0),
            purchase_id=purchase_id,
        ))

    return wine_name, total_bottles, groups


def parse_tasting_notes(html: str) -> tuple[str, str, list[TastingNote]]:
    """Parse tasting notes from the notes.asp page.

    HTML structure:
      div.wine_notes > h3 (wine name), span.score (avg score)
      ul.comments > li (each note):
        div.relative > h3: "date - author wrote/Likes: score"
        span.score > span.static: score number
        p.break_word: note text
    """
    soup = BeautifulSoup(html, "html.parser")

    # Wine name from header
    wine_notes_div = soup.find("div", class_="wine_notes")
    wine_name = ""
    avg_score = ""
    if wine_notes_div:
        h3 = wine_notes_div.find("h3")
        if h3:
            wine_name = h3.get_text(strip=True)

    # Avg score is in h2 > span.score inside div.panel
    for score_span in soup.find_all("span", class_="score"):
        text = score_span.get_text(strip=True)
        if "Avg" in text:
            match = re.search(r"([\d.]+)\s*points?", text)
            if match:
                avg_score = match.group(1)
            break

    # Parse individual notes
    notes = []
    comments_ul = soup.find("ul", class_="comments")
    if not comments_ul:
        return wine_name, avg_score, notes

    for li in comments_ul.find_all("li", recursive=False):
        if "divider" in " ".join(li.get("class", [])):
            continue

        h3 = li.find("h3")
        if not h3:
            continue

        # Date: text before " - " in h3
        h3_text = h3.get_text()
        note_date = ""
        if " - " in h3_text:
            note_date = h3_text.split(" - ")[0].strip()

        # Author: span.static inside the author link in h3
        author = ""
        author_link = h3.find("a", class_="hovercard")
        if author_link:
            static_span = author_link.find("span", class_="static")
            if static_span:
                author = static_span.get_text(strip=True)

        # Score: span.score > span.static (on the li, not the header)
        score = ""
        score_span = li.find("span", class_="score")
        if score_span:
            static = score_span.find("span", class_="static")
            if static:
                score = static.get_text(strip=True)

        # Note text
        note_p = li.find("p", class_="break_word")
        text = note_p.get_text(strip=True) if note_p else ""

        notes.append(TastingNote(
            author=author,
            date=note_date,
            score=score,
            text=text,
        ))

    return wine_name, avg_score, notes
