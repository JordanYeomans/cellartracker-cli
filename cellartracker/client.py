"""CellarTracker HTTP client - handles authentication and API interactions."""

from datetime import date

import requests

from cellartracker.models import PurchaseGroup, WineResult
from cellartracker.parsers import (
    parse_cellar_bottles,
    parse_pending_bottles,
    parse_search_results,
    parse_tasting_notes,
)

BASE_URL = "https://www.cellartracker.com"


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
        return parse_search_results(resp.text)

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
            results = parse_search_results(resp.text)
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

    def get_bottles(self, wine_id: int) -> tuple[str, int, list[PurchaseGroup]]:
        """Get individual bottles for a wine grouped by purchase.

        Checks both inmycellar.asp (cellar) and mypending.asp (pending).

        Returns:
            Tuple of (wine_name, total_bottles, list of PurchaseGroup)
        """
        self._ensure_logged_in()

        # Cellar bottles
        resp = self.session.get(
            f"{BASE_URL}/inmycellar.asp",
            params={"iWine": wine_id},
        )
        resp.raise_for_status()
        wine_name, total, groups = parse_cellar_bottles(resp.text)

        # Pending bottles
        resp2 = self.session.get(
            f"{BASE_URL}/mypending.asp",
            params={"iWine": wine_id},
        )
        resp2.raise_for_status()
        pending_name, pending_total, pending_groups = parse_pending_bottles(resp2.text)

        if not wine_name and pending_name:
            wine_name = pending_name
        total += pending_total
        groups.extend(pending_groups)

        return wine_name, total, groups

    def edit_purchase(
        self,
        wine_id: int,
        purchase_id: int,
        store: str | None = None,
        cost: str | None = None,
        currency: str | None = None,
        location: str | None = None,
        purchase_date: str | None = None,
    ) -> bool:
        """Edit an existing purchase.

        Only provided fields are changed; None fields are left as-is on the server.
        """
        self._ensure_logged_in()

        data: dict[str, str] = {
            "iWine": str(wine_id),
            "iPurchase": str(purchase_id),
            "Action": "Edit",
        }
        if store is not None:
            data["StoreName"] = store
        if cost is not None:
            data["BottleCost"] = cost
        if currency is not None:
            data["BottleCostCurrency"] = currency
        if location is not None:
            data["Location"] = location
            data["Location_1"] = location
        if purchase_date is not None:
            data["PurchaseDate"] = purchase_date

        resp = self.session.post(f"{BASE_URL}/purchase.asp", data=data)
        resp.raise_for_status()
        return resp.status_code == 200

    def delete_purchase(self, wine_id: int, purchase_id: int) -> bool:
        """Delete an entire purchase (all its bottles)."""
        self._ensure_logged_in()

        data = {
            "iWine": str(wine_id),
            "iPurchase": str(purchase_id),
            "Action": "Delete",
        }
        resp = self.session.post(f"{BASE_URL}/purchase.asp", data=data)
        resp.raise_for_status()
        return resp.status_code == 200

    def consume_bottle(
        self,
        wine_id: int,
        inventory_id: int | None = None,
        consumption_type: int = 0,
        drink_date: str | None = None,
        note: str = "",
    ) -> bool:
        """Consume/drink a bottle.

        Args:
            wine_id: CellarTracker wine ID
            inventory_id: Specific bottle to consume (if None, server picks first)
            consumption_type: 0=drank, 1=lost/destroyed, 2=gave away
            drink_date: Date consumed (MM/DD/YYYY), defaults to today
            note: Tasting note for the consumption
        """
        self._ensure_logged_in()

        if drink_date is None:
            drink_date = date.today().strftime("%m/%d/%Y")

        data: dict[str, str] = {
            "Choice": "dbDrink",
            "iWine": str(wine_id),
            "ConsumptionType": str(consumption_type),
            "DrinkDate": drink_date,
            "DrinkNote": note,
        }
        if inventory_id is not None:
            data["iInventory"] = str(inventory_id)

        resp = self.session.post(f"{BASE_URL}/barcode.asp", data=data)
        resp.raise_for_status()
        return resp.status_code == 200

    def deliver_purchase(self, wine_id: int, purchase_id: int) -> bool:
        """Accept delivery of a pending purchase."""
        self._ensure_logged_in()

        today = date.today().strftime("%m/%d/%Y")
        params = {
            "iWine": str(wine_id),
            "iPurchase": str(purchase_id),
            "DeliveryState": "delivered",
            "DeliveryDate": today,
        }
        resp = self.session.get(f"{BASE_URL}/purchase.asp", params=params)
        resp.raise_for_status()
        return resp.status_code == 200

    def get_tasting_notes(self, wine_id: int) -> tuple[str, str, list]:
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
        return parse_tasting_notes(resp.text)
