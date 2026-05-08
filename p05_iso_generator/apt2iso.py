# -*- coding: utf-8 -*-

from __future__ import annotations

from p02_machines_config.machine_parameters import JsonDict
from p05_iso_generator.apt_handlers import DISPATCH, h_default
from p05_iso_generator.apt_parser import normalize_apt_text, parse_keyword_and_rhs
from p05_iso_generator.iso_format import format_float_to_iso
from p05_iso_generator.iso_writer import IsoWriter
from p05_iso_generator.machine_state import WriterState


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


def convert_file(input_path: str, output_path: str, machine_config: JsonDict, channel_name: str) -> None:
    """Convertit un fichier APT en fichier ISO en utilisant les handlers definis ci-dessus."""
    with open(input_path, "r", encoding="utf-8", errors="replace") as input_file:
        apt_lines = normalize_apt_text(input_file.read()).splitlines()

    iso_lines = apt_to_iso_lines(apt_lines, machine_config, channel_name)

    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(iso_lines) + "\n")
