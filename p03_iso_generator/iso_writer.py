# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from p01_machines_config.machine_enums import FeedrateUnit, MotionMode, RotationDirection, RotationUnit, ToolComp, ToolType
from p01_machines_config.machine_parameters import JsonDict, MachineParameters
from p03_iso_generator.iso_format import format_float_to_iso
from p03_iso_generator.machine_state import (
    EmissionState,
    MachiningSelection,
    SpindleSelection,
    ToolSelection,
    ToolTransition,
    TransitionKind,
    get_machining_profile,
)


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

    # TODO: rotation_unit non utilisee. A implementer??
    def apply_tool_update(self, tool: ToolSelection, spindle: SpindleSelection,
                          position_x: float, position_c: float,
                          tool_change_processing: bool) -> ToolUpdateResult:
        """Emet les lignes ISO necessaires pour appliquer l'etat outil/broche courant."""

        # Controle minimal avant de choisir le profil MILL/TURN.
        if tool.tool_type is None:
            raise ValueError("MachiningProfileError: type outil absent avant changement outil/broche")

        # Validation de la selection outil/broche pour s'assurer que le changement d'outil/broche est coherent avec le profil de fraisage/tournage.
        selection = MachiningSelection(tool=tool, spindle=spindle)
        # Le profil de fraisage/tournage determine a partir du type d'outil valide la selection outil/broche pour s'assurer que le changement d'outil/broche est coherent avec le profil de fraisage/tournage.
        get_machining_profile(tool.tool_type).validate(selection, self.machine)

        # Determination de la transition outil/broche a partir de l'etat courant declare et du nouvel etat a emettre.
        transition = ToolTransition.from_emission_state(
            self.emission_state,
            tool,
            spindle,
            tool_change_processing,
        )
        # Validation de la transition pour s'assurer que les changements d'outil/broche sont coherents avec l'etat courant declare et le profil de fraisage/tournage.
        transition.validate()
        # Determination des lignes a emettre pour la transition outil/broche et emission de ces lignes.
        result = ToolUpdateResult()
        # Indicateur pour savoir si une rotation a deja ete emise par les codes de transition pour eviter les emissions redondantes de rotation.
        rotation_emitted = False

        # Si un changement d'outil doit etre traite, on emet les lignes de changement outil et de transition associees.
        if tool_change_processing:
            # Degagement avant changement outil si une position en X est connue pour eviter les collisions.
            self._emit_tool_clearance(position_x)
            # Emission de l'arret de l'ancien outil ou de l'ancienne broche si la transition l'exige.
            self._emit_previous_stop_for_transition(transition)
            # Emission du changement outil et des codes de transition specifiques au type de transition.
            self._emit_tool_change(tool)
            # Emission des codes de transition specifiques au type de transition et determination si une rotation a ete emise.
            rotation_emitted = self._emit_tool_transition(transition, result)

        # Si une rotation doit etre emise et n'a pas encore ete emise par les codes de transition, on l'emet.
        if transition.is_rotation_change and not rotation_emitted:
            # Emission de la rotation de broche ou d'outil tournant si elle n'a pas deja ete emise par les codes de transition.
            self._emit_rotation(tool, spindle)

        # Memorisation du nouvel etat outil/broche apres emission.
        self._store_tool_update(tool, spindle)
        # Retour des positions logiques forcees par l'emission de changement outil/broche pour que le post-processeur puisse les prendre en compte dans son etat courant declare.
        return result


    def _emit_tool_clearance(self, position_x: float) -> None:
        """Emet le degagement avant changement outil."""
        axis_words = [self.machine.rapid_move_code, f"{self.machine.toolname_prefix}0"]
        x_to_emit = position_x * 2 if self.machine.x_diameter else position_x
        axis_words.append(f"X{format_float_to_iso(x_to_emit)}")
        self.emit(f"{' '.join(axis_words)} (DEGAGEMENT OUTIL)")
        self.emission_state.last_x_position = position_x


    def _emit_tool_change(self, tool: ToolSelection) -> None:
        """Emet le commentaire et le bloc de changement outil."""
        self.emit(f"({self.machine.toolname_prefix}{tool.number:02d}{tool.number:02d} - {tool.comment})")
        self.emit(f"{self.machine.toolname_prefix}{tool.number:02d}{tool.number:02d}")


    def _emit_previous_stop_for_transition(self, transition: ToolTransition) -> None:
        """Arrete l'ancien outil ou l'ancienne broche si la transition l'exige."""
        if transition.previous_tool is None:
            return

        transition_kind = transition.kind()
        previous_tool_number = transition.previous_tool.number
        previous_spindle_number = (
            transition.previous_spindle.number
            if transition.previous_spindle is not None
            else None
        )

        if transition_kind == TransitionKind.TURN_TO_TURN and transition.is_spindle_change:
            self.spindle_stop(previous_tool_number, previous_spindle_number)
        elif transition_kind == TransitionKind.TURN_TO_MILL:
            self.spindle_stop(previous_tool_number, previous_spindle_number)
        elif transition_kind == TransitionKind.MILL_TO_TURN:
            self.spindle_stop(previous_tool_number, previous_spindle_number)
        elif transition_kind == TransitionKind.MILL_TO_MILL and transition.is_tool_number_change:
            self.spindle_stop(previous_tool_number, previous_spindle_number)


    def _emit_tool_transition(self, transition: ToolTransition, result: ToolUpdateResult) -> bool:
        """Emet les codes specifiques au type de transition et retourne True si la rotation est emise."""
        transition_kind = transition.kind()
        tool = transition.current_tool
        spindle = transition.current_spindle

        # Activation broche tournage apres premier outil TURN ou sortie du fraisage.
        if transition_kind in (TransitionKind.FIRST_TURN, TransitionKind.MILL_TO_TURN):
            self._emit_turn_activation(spindle, result)
            return True

        # Activation outil tournant de fraisage apres premier outil MILL, sortie du tournage ou changement d'outil de fraisage.
        if transition_kind in (TransitionKind.FIRST_MILL, TransitionKind.TURN_TO_MILL, TransitionKind.MILL_TO_MILL):
            self._emit_mill_activation(tool, spindle, result)
            return True

        # En TURN -> TURN, seule la broche ou la rotation peut necessiter une emission.
        if transition_kind == TransitionKind.TURN_TO_TURN:
            if transition.is_spindle_change:
                self.emit(self.machine.get_code_for_spindle_c_axis(spindle.number, False))
                self._emit_rotation(tool, spindle)
                return True
            if transition.is_rotation_change:
                self._emit_rotation(tool, spindle)
                return True
            return False

        # En MILL -> MILL, un nouvel outil doit etre demarre.
        if transition_kind == TransitionKind.MILL_TO_MILL:
            if transition.is_tool_number_change:
                self._emit_rotation(tool, spindle)
                return True
            return False

        return False


    def _emit_turn_activation(self, spindle: SpindleSelection, result: ToolUpdateResult) -> None:
        """Active une broche de tournage."""
        self.emit(self.machine.get_code_for_spindle_c_axis(spindle.number, False))
        self._emit_rotation_for_turn(spindle)
        self.emission_state.last_y_position = 0.0
        result.position_y = 0.0


    def _emit_mill_activation(self, tool: ToolSelection, spindle: SpindleSelection, result: ToolUpdateResult) -> None:
        """Active un outil tournant de fraisage et initialise l'axe C."""
        self._emit_rotation_for_mill(tool, spindle)
        self.emit(self.machine.get_code_for_spindle_c_axis(spindle.number, True))
        self.emit(self.machine.get_code_for_spindle_brake(spindle.number, False))
        self.emit(f"{self.machine.rapid_move_code} C{format_float_to_iso(0.0)}")
        self.emission_state.last_c_position = 0.0
        result.position_c = 0.0
        self.emit(self.machine.get_code_for_spindle_brake(spindle.number, True))


    def _emit_rotation(self, tool: ToolSelection, spindle: SpindleSelection) -> None:
        """Emet le code de rotation adapte au type d'outil courant."""
        if tool.tool_type == ToolType.TURN:
            self._emit_rotation_for_turn(spindle)
        elif tool.tool_type == ToolType.MILL:
            self._emit_rotation_for_mill(tool, spindle)


    def _emit_rotation_for_turn(self, spindle: SpindleSelection) -> None:
        """Emet la rotation de broche pour le tournage."""
        rotation_code = self.machine.get_code_for_turn_spindle(spindle.number, spindle.rotation_direction)
        self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(spindle.rotation_speed)}")


    def _emit_rotation_for_mill(self, tool: ToolSelection, spindle: SpindleSelection) -> None:
        """Emet la rotation de l'outil tournant pour le fraisage."""
        rotation_code = self.machine.get_code_for_tool_rotation(tool.number, spindle.rotation_direction)
        self.emit(f"{rotation_code} {self.machine.spindle_speed_prefix}{format_float_to_iso(spindle.rotation_speed)}")


    def _store_tool_update(self, tool: ToolSelection, spindle: SpindleSelection) -> None:
        """Memorise l'etat outil/broche qui vient d'etre emis."""
        self.emission_state.last_selection = MachiningSelection(
            tool=tool.copy(),
            spindle=spindle.copy(),
        )


    def _get_emitted_spindle_number(self) -> Optional[int]:
        """Retourne la derniere broche emise si elle existe."""
        if self.emission_state.last_selection is None:
            return None
        return self.emission_state.last_selection.spindle.number


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
            spindle_number = self._get_emitted_spindle_number()
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
        
