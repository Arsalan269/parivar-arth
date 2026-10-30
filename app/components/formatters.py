"""
Indian currency and number formatting utilities for Parivar Arth.
Follows Indian digit grouping: last 3 digits, then pairs of 2 digits (e.g. ₹1,25,000).
"""

from typing import Union


def format_inr(amount: Union[int, float], decimals: int = 0) -> str:
    """
    Format a number in Indian Rupee notation (e.g. 125000 -> ₹1,25,000).
    Handles negative numbers, zero, and floats.
    """
    if amount is None:
        return "₹0"
    
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹0"

    is_negative = val < 0
    val = abs(val)

    if decimals > 0:
        base_str = f"{val:.{decimals}f}"
        int_part, dec_part = base_str.split(".")
        dec_suffix = f".{dec_part}"
    else:
        int_part = str(int(round(val)))
        dec_suffix = ""

    # Indian grouping logic:
    # 1000 -> 1,000
    # 100000 -> 1,00,000
    # 10000000 -> 1,00,00,000
    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last3 = int_part[-3:]
        remaining = int_part[:-3]
        # Group remaining in blocks of 2 from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last3

    prefix = "-₹" if is_negative else "₹"
    return f"{prefix}{formatted_int}{dec_suffix}"


def format_inr_compact(amount: Union[int, float]) -> str:
    """
    Compact Indian currency notation (e.g. ₹1.25 L, ₹3.40 Cr, ₹45.2 K).
    """
    if amount is None:
        return "₹0"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹0"

    prefix = "-₹" if val < 0 else "₹"
    val = abs(val)

    if val >= 10000000:  # 1 Crore
        return f"{prefix}{val / 10000000:.2f} Cr"
    elif val >= 100000:   # 1 Lakh
        return f"{prefix}{val / 100000:.2f} L"
    elif val >= 1000:     # 1 Thousand
        return f"{prefix}{val / 1000:.1f} K"
    else:
        return f"{prefix}{int(val)}"


def format_pct(val: Union[int, float], decimals: int = 1, show_plus: bool = False) -> str:
    """Format percentage value."""
    if val is None:
        return "0.0%"
    try:
        v = float(val)
        plus = "+" if (show_plus and v > 0) else ""
        return f"{plus}{v:.{decimals}f}%"
    except (ValueError, TypeError):
        return "0.0%"
