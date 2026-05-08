# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from typing import Optional


def strip_comments(line_text: str) -> str:
    """Retire les commentaires inline pour simplifier le parsing."""
    stripped_line = line_text.rstrip("\n")
    for marker in ("!", "#", "//"):
        if marker in stripped_line:
            stripped_line = stripped_line.split(marker, 1)[0]
    return stripped_line.strip()


def parse_keyword_and_rhs(line_text: str) -> tuple[Optional[str], str]:
    """Extrait le mot-cle APT et le texte d'argument d'une ligne de code APT."""
    cleaned_line = strip_comments(line_text)
    if not cleaned_line:
        return None, ""

    if "/" in cleaned_line:
        apt_keyword, argument_text = cleaned_line.split("/", 1)
        apt_keyword = apt_keyword.strip().upper()
        if "," in apt_keyword:
            primary_keyword, secondary_keyword = apt_keyword.split(",", 1)
            return primary_keyword.strip(), f"{secondary_keyword.strip()}/{argument_text.strip()}"
        return apt_keyword, argument_text.strip()

    # fallback format "KEY args"
    apt_keyword, _, argument_text = cleaned_line.partition(" ")
    return apt_keyword.strip().upper(), argument_text.strip()


def csv_floats(argument_text: str) -> list[float]:
    """Parse une liste de nombres flottants separes par des virgules, en tolerant les espaces."""
    # Utilitaire pour les commandes du type GOTO/x,y,z
    return [float(token.strip()) for token in argument_text.split(",") if token.strip()]


def csv_tokens(argument_text: str) -> list[str]:
    """Parse une liste de tokens separes par des virgules, en tolerant les espaces."""
    return [token.strip() for token in argument_text.split(",") if token.strip()]


def normalize_apt_text(apt_text: str) -> str:
    """Normalise le texte APT avant decoupage en lignes logiques."""
    apt_text = re.sub(r"\$\r?\n", "", apt_text)
    apt_text = re.sub(r" {2,}", " ", apt_text)
    apt_text = re.sub(r"\t", " ", apt_text)
    return apt_text
