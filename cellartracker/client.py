"""CellarTracker HTTP client - handles authentication and API interactions."""

import re
from dataclasses import dataclass
from datetime import date

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cellartracker.com"


@dataclass
class TastingNote:
    author: str
    date: str
    score: str
    text: str

    def display(self) -> str:
        score_str = f" ({self.score} pts)" if self.score else ""
        header = f"{self.date} - {self.author}{score_str}"
        if self.text:
            return f"{header}\n    {self.text}"
        return header


@dataclass
class WineResult:
    wine_id: int
    vintage: str
    name: str
    region: str
    variety: str
    wine_type: str
    bottles: str
    score: str

    def display(self) -> str:
        score_str = f" | {self.score}" if self.score else ""
        bottles_str = f" {self.bottles}x" if self.bottles else ""
        return f"[{self.wine_id}]{bottles_str} {self.vintage} {self.name} - {self.region} ({self.variety}){score_str}"


class CellarTrackerClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })
        self._logged_in = False

    def login(self) -> bool:
        """Authenticate with CellarTracker via the classic login form."""
        # First GET the login page to obtain WAF token and cookies
        get_resp = self.session.get(f"{BASE_URL}/classic/password.asp")
        if get_resp.status_code == 403:
            # Try non-classic login
            get_resp = self.session.get(f"{BASE_URL}/password.asp")

        # Now POST login with session cookies (including WAF token)
        resp = self.session.post(
            f"{BASE_URL}/classic/password.asp",
            data={
                "szUser": self.username,
                "szPassword": self.password,
                "UseCookie": "true",
                "Referrer": "",
            },
            headers={
                "Referer": f"{BASE_URL}/classic/password.asp",
                "Origin": BASE_URL,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=True,
        )

        if resp.status_code == 403:
            # Fallback: try non-classic login
            get_resp = self.session.get(f"{BASE_URL}/password.asp")
            resp = self.session.post(
                f"{BASE_URL}/password.asp",
                data={
                    "szUser": self.username,
                    "szPassword": self.password,
                    "UseCookie": "true",
                    "Referrer": "",
                },
                headers={
                    "Referer": f"{BASE_URL}/password.asp",
                    "Origin": BASE_URL,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                allow_redirects=True,
            )

        resp.raise_for_status()

        # Check if login succeeded by looking for auth cookies
        cookies = {c.name: c.value for c in self.session.cookies}
        if "User" in cookies and "PWHash" in cookies:
            self._logged_in = True
            return True

        # Fallback: check if redirected to home page or if page contains welcome
        if "Welcome" in resp.text or "default.asp" in resp.url:
            self._logged_in = True
            return True

        return False

    def _ensure_logged_in(self):
        if not self._logged_in:
            if not self.login():
                raise RuntimeError("Failed to log in to CellarTracker")

    def search_wines(self, query: str, my_cellar: bool = False) -> list[WineResult]:
        """Search for wines by name, producer, or variety.

        Args:
            query: Search string
            my_cellar: If True, search only your cellar. If False, search all wines.
        """
        self._ensure_logged_in()

        params = {
            "Table": "List",
            "szSearch": query,
        }
        if my_cellar:
            params["fInStock"] = "1"
        else:
            params["fInStock"] = "0"
            params["iUserOverride"] = "0"

        resp = self.session.get(f"{BASE_URL}/list.asp", params=params)
        resp.raise_for_status()
        return self._parse_search_results(resp.text)

    def _parse_search_results(self, html: str) -> list[WineResult]:
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

    def add_wine(
        self,
        wine_id: int,
        quantity: int = 1,
        size: str = "750ml",
        pending: bool = False,
        location: str = "Cellar",
        bin_location: str = "",
        bottle_note: str = "",
        store: str = "",
        cost: str = "",
        currency: str = "USD",
        purchase_note: str = "",
    ) -> bool:
        """Add a wine to cellar or as pending delivery.

        Args:
            wine_id: CellarTracker wine ID (iWine)
            quantity: Number of bottles
            size: Bottle size (e.g., "750ml", "1.5L")
            pending: If True, set as "Pending Delivery" instead of "In My Cellar"
            location: Storage location name
            bin_location: Bin/slot within location
            bottle_note: Note about the bottle
            store: Store name where purchased
            cost: Cost per bottle
            currency: Currency code (e.g., "USD", "AUD")
            purchase_note: Note about the purchase
        """
        self._ensure_logged_in()

        today = date.today().strftime("%d/%m/%Y")
        delivery_state = "pending" if pending else "delivered"

        data = {
            "iWine": str(wine_id),
            "Action": "Add",
            "BinUI": "Single",
            "UISource": "list",
            "Quantity": str(quantity),
            "Size": size,
            "DeliveryState": delivery_state,
            "Location": location,
            "Location_1": location,
            "Bin": bin_location,
            "Bin_1": bin_location,
            "BottleNote": bottle_note,
            "StoreName": store,
            "PurchaseDate": today,
            "DeliveryDate": "",
            "BottleCostCurrency": currency,
            "BottleCost": cost,
            "PurchaseNote": purchase_note,
        }

        resp = self.session.post(f"{BASE_URL}/purchase.asp", data=data)
        resp.raise_for_status()

        # Check for success - after adding, CT typically redirects to the wine page
        if "wine.asp" in resp.url or resp.status_code == 200:
            # Verify it wasn't an error page
            if "error" not in resp.text.lower() or "cellar" in resp.text.lower():
                return True
        return False

    def _get_all_pages(self, params: dict) -> list[WineResult]:
        """Fetch all pages of a list endpoint and return combined results."""
        self._ensure_logged_in()

        all_results = []
        page = 1
        while True:
            p = {**params, "Page": str(page)}
            resp = self.session.get(f"{BASE_URL}/list.asp", params=p)
            resp.raise_for_status()
            results = self._parse_search_results(resp.text)
            if not results:
                break
            all_results.extend(results)
            # If we got fewer than 100, we're on the last page
            if len(results) < 100:
                break
            page += 1
        return all_results

    def get_my_cellar(self) -> list[WineResult]:
        """Get all wines currently in your cellar, sorted alphabetically."""
        results = self._get_all_pages({"Table": "List", "O": "SortWine"})
        results.sort(key=lambda w: w.name.lower())
        return results

    def get_pending(self) -> list[WineResult]:
        """Get all wines pending delivery, sorted alphabetically."""
        results = self._get_all_pages({"Table": "Pending", "O": "SortWine"})
        results.sort(key=lambda w: w.name.lower())
        return results

    def get_tasting_notes(self, wine_id: int) -> tuple[str, str, list[TastingNote]]:
        """Get community tasting notes for a wine.

        Returns:
            Tuple of (wine_name, avg_score, list of TastingNote)
        """
        self._ensure_logged_in()

        resp = self.session.get(
            f"{BASE_URL}/notes.asp",
            params={"iWine": wine_id},
        )
        resp.raise_for_status()
        return self._parse_tasting_notes(resp.text)

    def _parse_tasting_notes(self, html: str) -> tuple[str, str, list[TastingNote]]:
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
