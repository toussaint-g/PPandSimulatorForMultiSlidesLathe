# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from p01_machines_config.machine_enums import FeedrateUnit, MotionMode, SpindleDirection, SpindleUnit, ToolComp
from p01_machines_config.machine_parameters import JsonDict, MachineParameters
from p03_iso_generator.iso_format import format_float_to_iso
from p03_iso_generator.machine_state import EmissionState


class IsoWriter:
    """Helper pour construire un programme ISO ligne par ligne a partir de l'etat du post-processeur."""

    def __init__(self, machine_config: JsonDict, channel_name: str) -> None:
        """Initialise le writer avec un etat vide et une liste de lignes ISO vide."""
        # out contient le programme ISO final, ligne par ligne.
        self.out: list[str] = []
        self.emission_state = EmissionState()
        self.machine = MachineParameters.from_config(machine_config, channel_name)


    def emit(self, iso_line: str) -> None:
        """Ajoute une ligne ISO a la sortie."""
        self.out.append(iso_line)


    def comment(self, comment_text: str) -> None:
        """Ajoute un commentaire ISO a la sortie."""
        self.emit(f"({comment_text})")


    def insert(self, insert_text: str) -> None:
        """Ajoute une ligne d'insertion a la sortie."""
        self.emit(f"{insert_text}")


    def header(self) -> None:
        """Ajoute l'en-tete minimal pour un programme de fraisage en coordonnees absolues."""
        self.emit(f"{self.machine.startandendfile_character}")
        self.emit(f"{self.machine.program_prefix}{self.machine.channel_name}000")


    def footer(self, tool_number: int) -> None:
        """Ajoute le pied de page minimal pour un programme de fraisage."""
        self.emit(self.machine.get_spindle_code_for_tool(tool_number))
        self.emit(f"{self.machine.endprogram_code}")
        self.emit(f"{self.machine.startandendfile_character}")


    def op_name(self, bloc_number: int, op_name: str) -> None:
        """Ajoute un commentaire d'operation avec le numero de bloc."""
        self.emit(f"{self.machine.block_prefix}{bloc_number} ({op_name})")


    def channel(self, channel_number: int) -> None:
        """Ajoute un commentaire de canal."""
        self.emit(f"(CANAL {channel_number})")


    def tool_change(self, tool_number: int, tool_comment: str, position_x: float, position_y: float, position_z: float) -> None:
        """Emet les lignes ISO pour un changement d'outil, en fonction du type d'outil et de l'etat de la broche."""
        x_to_emit = position_x * 2 if self.machine.x_diameter else position_x
        self.emission_state.last_x_position = position_x
        self.emit(f"{self.machine.rapid_move_code} {self.machine.toolname_prefix}0 X{format_float_to_iso(x_to_emit)} (DEGAGEMENT OUTIL)")
        self.emit(f"({self.machine.toolname_prefix}{tool_number:02d}{tool_number:02d} - {tool_comment})")
        self.emit(f"{self.machine.toolname_prefix}{tool_number:02d}{tool_number:02d}")


    # TODO: Gestion surface constante (G96/G97) pas prise en compte pour l'instant, a voir si on en a besoin.
    def spindle_start(self, tool_number: int, spindle_speed: float, spindle_unit: SpindleUnit, spindle_direction: SpindleDirection) -> None:
        """Demarre la broche avec la vitesse et la direction specifiees."""
        if self.emission_state.last_spindle_speed != spindle_speed or self.emission_state.last_spindle_direction != spindle_direction or self.emission_state.last_tool_number != tool_number:
            self.emit(f"{self.machine.get_spindle_code_for_tool(tool_number, spindle_direction)} {self.machine.spindle_speed_prefix}{format_float_to_iso(spindle_speed)}")
            self.emission_state.last_spindle_speed = spindle_speed
            self.emission_state.last_spindle_direction = spindle_direction
            self.emission_state.last_tool_number = tool_number


    def spindle_stop(self, tool_number: int) -> None:
        """Arrete la broche."""
        self.emit(self.machine.get_spindle_code_for_tool(tool_number))


    def linear_move(self, tool_number: int, motion_mode: MotionMode, cutcom_mode: ToolComp, feedrate_value: float,
                    feedrate_unit: Optional[FeedrateUnit], position_x=None, position_y=None, position_z=None,
                    position_c=None) -> None:
        """Gere les mouvements lineaires en emettant le code de mouvement approprie et les coordonnees qui ont change."""
        motion_code = self.machine.rapid_move_code if motion_mode == MotionMode.RAPID else self.machine.linear_move_code
        axis_words = [motion_code]

        # Si le mode de compensation d'outil a change, on l'ajoute a la ligne de mouvement.
        if self.emission_state.last_toolComp_mode != cutcom_mode:
            axis_words.append(self.machine.get_tool_compensation_code_for_tool(tool_number, cutcom_mode))
            self.emission_state.last_toolComp_mode = cutcom_mode

        # Si une coordonnee a change, on l'ajoute a la ligne de mouvement et on met a jour la position courante.
        if position_x is not None:
            x_to_emit = position_x * 2 if self.machine.x_diameter else position_x
            self.emission_state.last_x_position = position_x
            axis_words.append(f"X{format_float_to_iso(x_to_emit)}")
        if position_y is not None:
            axis_words.append(f"Y{format_float_to_iso(position_y)}")
            self.emission_state.last_y_position = position_y
        if position_z is not None:
            axis_words.append(f"Z{format_float_to_iso(position_z)}")
            self.emission_state.last_z_position = position_z
        if position_c is not None:
            axis_words.append(f"C{format_float_to_iso(position_c)}")
            self.emission_state.last_c_position = position_c

        # Si l'unite d'avance a change, on l'ajoute a la ligne de mouvement.
        if self.emission_state.last_feedrate_unit != feedrate_unit:
            if feedrate_unit == FeedrateUnit.MMPM:
                axis_words.append(f"{self.machine.feedrate_per_minute}")
                self.emission_state.last_feedrate_unit = FeedrateUnit.MMPM
            else:
                axis_words.append(f"{self.machine.feedrate_per_revolution}")
                self.emission_state.last_feedrate_unit = FeedrateUnit.MMPR

        # Si l'avance a change, on l'ajoute a la ligne de mouvement.
        if self.emission_state.last_feedrate_value != feedrate_value:
            axis_words.append(f"F{format_float_to_iso(feedrate_value)}")
            self.emission_state.last_feedrate_value = feedrate_value

        # Si au moins une information a changee, on emet la ligne de mouvement.
        self.emit(" ".join(axis_words))


    def circular_move(self, work_plane: str, motion_code: str, feedrate_value: float, feedrate_unit: Optional[FeedrateUnit],
                      center_x: float, center_y: float, center_z: float,
                      position_x=None, position_y=None, position_z=None) -> None:
        """Gere les mouvements circulaires en emettant le plan, le code et les offsets de centre."""
        axis_words = []

        if self.emission_state.last_work_plane_code != work_plane:
            axis_words.append(work_plane)
            self.emission_state.last_work_plane_code = work_plane

        axis_words.append(motion_code)

        initial_home_x, initial_home_y, initial_home_z = self.machine.get_initial_home_tool()
        start_x = self.emission_state.last_x_position if self.emission_state.last_x_position is not None else initial_home_x
        start_y = self.emission_state.last_y_position if self.emission_state.last_y_position is not None else initial_home_y
        start_z = self.emission_state.last_z_position if self.emission_state.last_z_position is not None else initial_home_z

        if position_x is not None:
            x_to_emit = position_x * 2 if self.machine.x_diameter else position_x
            axis_words.append(f"X{format_float_to_iso(x_to_emit)}")
            self.emission_state.last_x_position = position_x
        if position_y is not None:
            axis_words.append(f"Y{format_float_to_iso(position_y)}")
            self.emission_state.last_y_position = position_y
        if position_z is not None:
            axis_words.append(f"Z{format_float_to_iso(position_z)}")
            self.emission_state.last_z_position = position_z

        start_x_for_offset = start_x

        if work_plane == self.machine.xy_work_plane_code:
            axis_words.append(f"I{format_float_to_iso(center_x - start_x_for_offset)}")
            axis_words.append(f"J{format_float_to_iso(center_y - start_y)}")
        elif work_plane == self.machine.xz_work_plane_code:
            axis_words.append(f"I{format_float_to_iso(center_x - start_x_for_offset)}")
            axis_words.append(f"K{format_float_to_iso(center_z - start_z)}")
        else:
            axis_words.append(f"J{format_float_to_iso(center_y - start_y)}")
            axis_words.append(f"K{format_float_to_iso(center_z - start_z)}")

        if self.emission_state.last_feedrate_unit != feedrate_unit:
            if feedrate_unit == FeedrateUnit.MMPM:
                axis_words.append(f"{self.machine.feedrate_per_minute}")
                self.emission_state.last_feedrate_unit = FeedrateUnit.MMPM
            else:
                axis_words.append(f"{self.machine.feedrate_per_revolution}")
                self.emission_state.last_feedrate_unit = FeedrateUnit.MMPR
        if self.emission_state.last_feedrate_value != feedrate_value:
            axis_words.append(f"F{format_float_to_iso(feedrate_value)}")
            self.emission_state.last_feedrate_value = feedrate_value

        self.emit(" ".join(axis_words))
