# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from p01_machines_config.machine_parameters import JsonDict
from p03_iso_generator.apt_handlers import DISPATCH, h_default
from p03_iso_generator.apt_parser import normalize_apt_text, parse_keyword_and_rhs
from p03_iso_generator.iso_writer import IsoWriter
from p03_iso_generator.machine_state import WriterState


def _is_unmanaged_debug_line(iso_line: str) -> bool:
    """Indique si une ligne est un diagnostic de commande non geree."""
    return iso_line.startswith("(NON GERE:")


def apt_to_iso_lines(apt_lines: list[str], machine_config: JsonDict, channel_name: str) -> list[str]:
    """Convertit une liste de lignes APT en lignes ISO."""
    state = WriterState()
    iso_writer = IsoWriter(machine_config, channel_name)
    iso_writer.header()

    for line_number, line_text in enumerate(apt_lines, start=1):
        state.line_number = line_number
        apt_keyword, argument_text = parse_keyword_and_rhs(line_text)
        if apt_keyword is None:
            continue

        handler = DISPATCH.get(apt_keyword, h_default)
        handler(apt_keyword, argument_text, state, iso_writer)

        # END termine explicitement le programme APT.
        if apt_keyword == "END":
            break

    return iso_writer.out


def apt_to_debug_and_nc_lines(apt_lines: list[str], machine_config: JsonDict, channel_name: str) -> tuple[list[str], list[str]]:
    """Convertit des lignes APT en sortie debug complete et sortie NC exploitable."""
    debug_lines = apt_to_iso_lines(apt_lines, machine_config, channel_name)
    nc_lines = [iso_line for iso_line in debug_lines if not _is_unmanaged_debug_line(iso_line)]
    return debug_lines, nc_lines


def _write_lines(output_path: str, lines: list[str]) -> None:
    """Ecrit une liste de lignes avec des fins de ligne UNIX."""
    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines) + "\n")


def convert_file(input_path: str, debug_output_path: str, machine_config: JsonDict, channel_name: str, nc_output_path: str | None = None) -> None:
    """Convertit un fichier APT en fichiers debug et NC."""
    with open(input_path, "r", encoding="utf-8", errors="replace") as input_file:
        apt_lines = normalize_apt_text(input_file.read()).splitlines()

    debug_lines, nc_lines = apt_to_debug_and_nc_lines(apt_lines, machine_config, channel_name)

    _write_lines(debug_output_path, debug_lines)
    _write_lines(nc_output_path or str(Path(debug_output_path).with_suffix(".nc")), nc_lines)
