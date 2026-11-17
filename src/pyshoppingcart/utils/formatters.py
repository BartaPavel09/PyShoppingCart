"""Monetary and text formatting utilities for PyShoppingCart.

Guarantees 100% integer cent arithmetic with zero float conversion errors.
"""

from __future__ import annotations


def cents_to_usd(cents: int) -> str:
    """Format integer cents into a USD dollar string (e.g. 1999 -> '$19.99')."""
    sign = "-" if cents < 0 else ""
    abs_cents = abs(cents)
    dollars = abs_cents // 100
    rem = abs_cents % 100
    return f"{sign}${dollars}.{rem:02d}"


def usd_to_cents(usd_str: str) -> int:
    """Parse user-provided dollar string to integer cents without floating point math.

    Examples:
        '19.99' -> 1999
        '$19.99' -> 1999
        '10' -> 1000
        '0.5' -> 50
    """
    cleaned = usd_str.strip().lstrip("$").strip()
    if "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid monetary format: {usd_str}")
        dollars_part = int(parts[0] or "0")
        cents_part = parts[1][:2].ljust(2, "0")
        return dollars_part * 100 + int(cents_part)
    return int(cleaned) * 100
