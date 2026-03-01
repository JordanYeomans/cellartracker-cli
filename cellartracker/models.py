"""Data models for CellarTracker wines, bottles, and tasting notes."""

from collections import Counter
from dataclasses import dataclass


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
class BottleInfo:
    number: str
    barcode: str
    size: str
    status: str
    location: str
    bin: str
    note: str
    inventory_id: str = ""


@dataclass
class PurchaseGroup:
    quantity: str
    size: str
    store: str
    purchase_date: str
    cost_per_bottle: str
    bottles: list[BottleInfo]
    purchase_id: str = ""

    def display(self) -> str:
        prefix = f"[{self.purchase_id}] " if self.purchase_id else ""
        parts = [f"{prefix}{self.quantity}x {self.size}"]
        if self.store:
            parts.append(f"from {self.store}")
        if self.purchase_date:
            parts.append(f"on {self.purchase_date}")
        if self.cost_per_bottle:
            parts.append(f"@ {self.cost_per_bottle}/bottle")
        header = " ".join(parts)
        lines = [header]

        # List bottles individually when they have inventory_ids, otherwise summarize
        has_ids = any(b.inventory_id for b in self.bottles)
        if has_ids:
            for b in self.bottles:
                bottle_parts = []
                if b.inventory_id:
                    bottle_parts.append(f"[{b.inventory_id}]")
                if b.location:
                    bottle_parts.append(b.location)
                if b.bin and b.bin != "n/a":
                    bottle_parts.append(f"bin {b.bin}")
                if b.status and b.status != "In my cellar":
                    bottle_parts.append(b.status)
                if b.note and b.note != "n/a":
                    bottle_parts.append(f'"{b.note}"')
                if bottle_parts:
                    lines.append(f"    {' | '.join(bottle_parts)}")
        else:
            details = Counter()
            for b in self.bottles:
                bottle_parts = []
                if b.location:
                    bottle_parts.append(b.location)
                if b.bin and b.bin != "n/a":
                    bottle_parts.append(f"bin {b.bin}")
                if b.status and b.status != "In my cellar":
                    bottle_parts.append(b.status)
                if b.note and b.note != "n/a":
                    bottle_parts.append(f'"{b.note}"')
                if bottle_parts:
                    details[" | ".join(bottle_parts)] += 1

            for detail, count in details.items():
                if count > 1:
                    lines.append(f"    {count}x {detail}")
                else:
                    lines.append(f"    {detail}")
        return "\n".join(lines)


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
