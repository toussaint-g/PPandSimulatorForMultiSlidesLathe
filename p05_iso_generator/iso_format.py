# -*- coding: utf-8 -*-

from __future__ import annotations


def format_float_to_iso(numeric_value: float) -> str:
    """Formatte un nombre pour l'ISO en supprimant les zeros inutiles."""
    formatted_value = f"{numeric_value:.3f}".rstrip("0").rstrip(".")
    return formatted_value if formatted_value else "0"
