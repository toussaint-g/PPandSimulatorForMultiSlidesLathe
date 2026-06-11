# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from p01_machines_config.machine_enums import FeedrateUnit, MotionMode, RotationDirection, RotationUnit, ToolComp, ToolType
from p01_machines_config.machine_parameters import JsonDict, MachineParameters
from p03_iso_generator.iso_format import format_float_to_iso
from p03_iso_generator.machine_state import EmissionState


@dataclass
class ToolUpdateResult:
    """Positions logiques forcees par une emission de changement outil."""
    position_y: float | None = None
    position_c: float | None = None


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


    def footer(self, tool_number: int, spindle_number: Optional[int] = None) -> None:
        """Ajoute le pied de page minimal pour un programme de fraisage."""
        self.emit(self.machine.get_spindle_code(tool_number, spindle_number))
        self.emit(f"{self.machine.endprogram_code}")
        self.emit(f"{self.machine.startandendfile_character}")


    def op_name(self, bloc_number: int, op_name: str) -> None:
        """Ajoute un commentaire d'operation avec le numero de bloc."""
        self.emit(f"{self.machine.block_prefix}{bloc_number} ({op_name})")


    def channel(self, channel_number: int) -> None:
        """Ajoute un commentaire de canal."""
        self.emit(f"(CANAL {channel_number})")
















    # TODO: reprendre cette partie car generation de C0 lors des changements de C.

    # TODO: rotation_unit non utilisee. A implementer??
    def apply_tool_update(self, tool_comment: str, tool_number: int, tool_type: ToolType, linked_spindle_number: Optional[int],
                          spindle_number: int,
                          rotation_speed: float, rotation_unit: RotationUnit, rotation_direction: RotationDirection,
                          position_x: float, position_c: float,
                          tool_change_processing: bool) -> ToolUpdateResult:
        """Emet les lignes ISO necessaires pour appliquer un changement d'outil et les changements de position logiques associes."""
        


        





        result = ToolUpdateResult()










        # Si changement d'outil (donc LOADTL dans APT), on emet les lignes de changement d'outil et on met a jour l'emission state en consequence.
        if tool_change_processing:
            # Degagement de l'outil avant changement.
            axis_words = [self.machine.rapid_move_code, f"{self.machine.toolname_prefix}0"]
            x_to_emit = position_x * 2 if self.machine.x_diameter else position_x
            axis_words.append(f"X{format_float_to_iso(x_to_emit)}")
            self.emit(f"{' '.join(axis_words)} (DEGAGEMENT OUTIL)")
            self.emission_state.last_x_position = position_x

            # Si outil precedent not None, changement d'outil et nouvel outil de type MILL, on l'arrete.
            if (self.emission_state.last_tool_number is not None and 
                self.emission_state.last_tool_number != tool_number and 
                tool_type == ToolType.MILL
                ):
                self.spindle_stop(self.emission_state.last_tool_number, self.emission_state.last_spindle_number)

            # Commentaire et changement d'outil.
            self.emit(f"({self.machine.toolname_prefix}{tool_number:02d}{tool_number:02d} - {tool_comment})")
            self.emit(f"{self.machine.toolname_prefix}{tool_number:02d}{tool_number:02d}")

            # Si 1er outil et de type TURN ou changement d'outil de type MILL vers TURN.
            if (self.emission_state.last_tool_type == None and tool_type == ToolType.TURN) or (
                self.emission_state.last_tool_type == ToolType.MILL and tool_type == ToolType.TURN
                ):
                self.emit(self.machine.get_code_for_spindle_c_axis(spindle_number, False))
                rotation_code = self.machine.get_code_for_turn_spindle(spindle_number, rotation_direction)
                self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(rotation_speed)}")
                self.emission_state.last_y_position = 0.0
                result.position_y = 0.0
                
            # Si 1er outil et de type MILL ou changement d'outil de type TURN vers MILL.
            elif (self.emission_state.last_tool_type == None and tool_type == ToolType.MILL) or (
                self.emission_state.last_tool_type == ToolType.TURN and tool_type == ToolType.MILL
                ):
                rotation_code = self.machine.get_code_for_tool_rotation(tool_number, rotation_direction)
                self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(rotation_speed)}")
                self.emit(self.machine.get_code_for_spindle_c_axis(spindle_number, True))
                self.emit(self.machine.get_code_for_spindle_brake(spindle_number, False))
                self.emit(f"{self.machine.rapid_move_code} C{format_float_to_iso(0.0)}")
                self.emission_state.last_c_position = 0.0
                result.position_c = 0.0
                self.emit(self.machine.get_code_for_spindle_brake(spindle_number, True))

            # Si changement d'outil TURN vers TURN.
            elif self.emission_state.last_tool_type == ToolType.TURN and tool_type == ToolType.TURN:
                if self.emission_state.last_spindle_number != spindle_number:
                    self.emit(self.machine.get_code_for_spindle_c_axis(spindle_number, False))
                    rotation_code = self.machine.get_code_for_turn_spindle(spindle_number, rotation_direction)
                    self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(rotation_speed)}")
                elif self.emission_state.last_rotation_speed != rotation_speed or self.emission_state.last_rotation_direction != rotation_direction:
                    rotation_code = self.machine.get_code_for_turn_spindle(spindle_number, rotation_direction)
                    self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(rotation_speed)}")

            # Si changement d'outil MILL vers MILL.
            elif self.emission_state.last_tool_type == ToolType.MILL and tool_type == ToolType.MILL:
                # Si nouvel outil, on le met en rotation avec les bons codes.
                if self.emission_state.last_tool_number != tool_number:
                    rotation_code = self.machine.get_code_for_tool_rotation(tool_number, rotation_direction)
                    self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(rotation_speed)}")
            









        else:
            # Si pas de changement d'outil mais changement de broche, message d'erreur car changement d'outil requis.
            if self.emission_state.last_spindle_number != spindle_number:
                raise ValueError(f"CatiaConfigError: changement de broche impossible sans changement d'outil prealable : {spindle_number}")
            











        # Si changement de vitesse de rotation, d'unite ou de direction, on emet le bon code de rotation et on change la vitesse.
        if (self.emission_state.last_rotation_speed is not None and
            (rotation_speed != self.emission_state.last_rotation_speed or 
            rotation_unit != self.emission_state.last_rotation_unit or 
            rotation_direction != self.emission_state.last_rotation_direction)
            ):
            if tool_type == ToolType.TURN:
                rotation_code = self.machine.get_code_for_turn_spindle(spindle_number, rotation_direction)
            elif tool_type == ToolType.MILL:
                rotation_code = self.machine.get_code_for_tool_rotation(tool_number, rotation_direction)
            self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(rotation_speed)}")






        # Mise a jour de l'emission state apres emission du changement d'outil.
        self.emission_state.last_tool_number = tool_number
        self.emission_state.last_tool_type = tool_type
        self.emission_state.last_linked_spindle_number = linked_spindle_number
        self.emission_state.last_spindle_number = spindle_number
        self.emission_state.last_rotation_speed = rotation_speed
        self.emission_state.last_rotation_unit = rotation_unit
        self.emission_state.last_rotation_direction = rotation_direction
        return result













    def spindle_stop(self, tool_number: int, spindle_number: Optional[int] = None) -> None:
        """Arrete la broche."""
        self.emit(self.machine.get_spindle_code(tool_number, spindle_number))









    # TODO: a verifier.
    def linear_move(self, tool_number: int, motion_mode: MotionMode, cutcom_mode: ToolComp, feedrate_value: float,
                    feedrate_unit: Optional[FeedrateUnit], position_x=None, position_y=None, position_z=None,
                    position_c=None) -> None:
        """Gere les mouvements lineaires en emettant le code de mouvement approprie et les coordonnees qui ont change."""

        # Si une position en axe C est fournie, on emet le code de mouvement en axe C avant les autres axes pour eviter les collisions.
        if position_c is not None:
            # Si une rotation en axe C est demandee, on emet le code de desactivation et reactivation du frein de broche.
            spindle_number = self.emission_state.last_spindle_number
            self.emit(self.machine.get_code_for_spindle_brake(spindle_number, False))
            self.emit(f"{self.machine.rapid_move_code} C{format_float_to_iso(position_c)}")
            self.emit(self.machine.get_code_for_spindle_brake(spindle_number, True))
            self.emission_state.last_c_position = position_c




        # Determination du code de mouvement lineaire ou rapide et construction de la ligne de mouvement avec les axes qui ont change.
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

        initial_tool_change_x, initial_tool_change_y, initial_tool_change_z = self.machine.get_initial_tool_change_point()
        start_x = self.emission_state.last_x_position if self.emission_state.last_x_position is not None else initial_tool_change_x
        start_y = self.emission_state.last_y_position if self.emission_state.last_y_position is not None else initial_tool_change_y
        start_z = self.emission_state.last_z_position if self.emission_state.last_z_position is not None else initial_tool_change_z

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








    # TODO: a finaliser apres verification des mouvements en axe C.
    def caxis_move(self, tool_number: int, spindle_number: Optional[int], rotation_speed: float, rotation_unit: RotationUnit,
                   rotation_direction: RotationDirection, position_c: float) -> None:
        """Gere les mouvements en axe C en emettant le code de rotation de broche approprie et la position C."""
        
