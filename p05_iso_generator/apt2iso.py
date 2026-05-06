# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
from functools import partial
import re
from p02_machines_config.machine_parameters import JsonDict, MachineParameters
from p02_machines_config.machine_enums import FeedrateUnit, MotionMode, SpindleDirection, SpindleUnit, ToolComp, ToolType
from p05_iso_generator.geometric_calculations import line_circle_intersections_2d as geometry_line_circle_intersections_2d
from p05_iso_generator.machine_state import EmissionState, WriterState


# -----------------------------
# Outils formatage ISO
# -----------------------------
def format_float_to_iso(numeric_value: float) -> str:
    """Formatte un nombre pour l'ISO en supprimant les zeros inutiles."""
    formatted_value = f"{numeric_value:.3f}".rstrip("0").rstrip(".")
    return formatted_value if formatted_value else "0"







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

    def footer(self) -> None:
        """Ajoute le pied de page minimal pour un programme de fraisage."""
        self.emit(f"{self.machine.endprogram_code}")
        self.emit(f"{self.machine.startandendfile_character}")

    def op_name(self, bloc_number: int, op_name: str) -> None:
        """Ajoute un commentaire d'operation avec le numero de bloc."""
        self.emit(f"{self.machine.block_prefix}{bloc_number} ({op_name})")

    def channel(self, channel_number: int) -> None:
        """Ajoute un commentaire de canal."""
        self.emit(f"(CANAL {channel_number})")

    # TODO: Pas assez de verif, a reprendre

    def tool_change(self, tool_number: int, tool_comment: str) -> None:
        """Emet les lignes ISO pour un changement d'outil, en fonction du type d'outil et de l'etat de la broche."""
        
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
                    feedrate_unit: Optional[FeedrateUnit], position_x=None, position_y=None, position_z=None) -> None:
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

        start_x = self.emission_state.last_x_position if self.emission_state.last_x_position is not None else self.machine.home_tool_x
        start_y = self.emission_state.last_y_position if self.emission_state.last_y_position is not None else self.machine.home_tool_y
        start_z = self.emission_state.last_z_position if self.emission_state.last_z_position is not None else self.machine.home_tool_z

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


# -----------------------------
# Parsing APT (rigide)
# -----------------------------
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


# -----------------------------
# Handlers APT -> ISO
# -----------------------------
# Chaque handler traduit une instruction APT en mise a jour d'etat
# et/ou en emission d'une ou plusieurs lignes ISO.
Handler = Callable[[str, str, WriterState, IsoWriter], None]


@dataclass
class TlonArcDefinition:
    """Definition normalisee d'un raccord TLON base sur une geometrie CATIA."""

    geometry_kind: str
    start_x: float
    start_y: float
    start_z: float
    tangent_x: float
    tangent_y: float
    tangent_z: float
    center_x: float
    center_y: float
    center_z: float
    radius: float
    end_x: float
    end_y: float
    end_z: float
    raw_argument_text: str
    axis_u: float | None = None
    axis_v: float | None = None
    axis_w: float | None = None


@dataclass
class TlonArcSolution:
    """Resultat geometrique d'un TLON pret a etre emis en ISO."""

    work_plane_code: str
    motion_code: str
    center_x: float
    center_y: float
    center_z: float
    end_x: float
    end_y: float
    end_z: float


def emit_tlon_not_supported(argument_text: str, iso_writer: IsoWriter, reason: str | None = None) -> None:
    """Centralise les messages de non-support pour TLON."""
    if reason:
        iso_writer.comment(f"NON GERE: TLON/{argument_text} ({reason})")
        return
    iso_writer.comment(f"NON GERE: TLON/{argument_text}")


def parse_tlon_circle_definition(argument_text: str, state: WriterState) -> TlonArcDefinition | None:
    """Parse la variante CATIA TLON basee sur CIRCLE et retourne une definition normalisee."""
    geometry_match = re.search(r"\(CIRCLE/\s*([^)]+?)\s*\),\s*ON,\s*\(LINE/\s*([^)]+?)\s*\)", argument_text, re.IGNORECASE)
    if not geometry_match:
        return None

    circle_definition_values = csv_floats(geometry_match.group(1))
    line_definition_values = csv_floats(geometry_match.group(2))
    if len(circle_definition_values) != 4 or len(line_definition_values) != 6:
        return None

    center_x, center_y, center_z, radius = circle_definition_values
    _, _, _, end_x, end_y, end_z = line_definition_values

    return TlonArcDefinition(
        geometry_kind="CIRCLE",
        start_x=state.position_x,
        start_y=state.position_y,
        start_z=state.position_z,
        tangent_x=state.indirv_x if state.indirv_x is not None else 0.0,
        tangent_y=state.indirv_y if state.indirv_y is not None else 0.0,
        tangent_z=state.indirv_z if state.indirv_z is not None else 0.0,
        center_x=center_x,
        center_y=center_y,
        center_z=center_z,
        radius=radius,
        end_x=end_x,
        end_y=end_y,
        end_z=end_z,
        raw_argument_text=argument_text,
    )


def parse_tlon_cylndr_definition(argument_text: str, state: WriterState) -> TlonArcDefinition | None:
    """Parse la variante CATIA TLON basee sur CYLNDR et retourne une definition normalisee."""
    geometry_match = re.search(r"\(CYLNDR/\s*([^)]+?)\s*\)", argument_text, re.IGNORECASE)
    if not geometry_match:
        return None

    cylinder_definition_values = csv_floats(geometry_match.group(1))
    if len(cylinder_definition_values) != 7:
        return None

    point_matches = re.findall(r"\(POINT/\s*([^)]+?)\s*\)", argument_text, re.IGNORECASE)
    if not point_matches:
        return None

    end_point_values = csv_floats(point_matches[-1])
    if len(end_point_values) != 3:
        return None

    center_x, center_y, center_z, axis_u, axis_v, axis_w, radius = cylinder_definition_values
    end_x, end_y, end_z = end_point_values

    return TlonArcDefinition(
        geometry_kind="CYLNDR",
        start_x=state.position_x,
        start_y=state.position_y,
        start_z=state.position_z,
        tangent_x=state.indirv_x if state.indirv_x is not None else 0.0,
        tangent_y=state.indirv_y if state.indirv_y is not None else 0.0,
        tangent_z=state.indirv_z if state.indirv_z is not None else 0.0,
        center_x=center_x,
        center_y=center_y,
        center_z=center_z,
        radius=radius,
        end_x=end_x,
        end_y=end_y,
        end_z=end_z,
        axis_u=axis_u,
        axis_v=axis_v,
        axis_w=axis_w,
        raw_argument_text=argument_text,
    )


def parse_tlon_definition(argument_text: str, state: WriterState) -> TlonArcDefinition | None:
    """Retourne la definition TLON normalisee correspondant a la geometrie detectee."""
    tlon_definition = parse_tlon_circle_definition(argument_text, state)
    if tlon_definition is not None:
        return tlon_definition
    return parse_tlon_cylndr_definition(argument_text, state)


def solve_tlon_circle_xy(definition: TlonArcDefinition, state: WriterState, iso_writer: IsoWriter) -> TlonArcSolution | None:
    """Resout geometriquement un TLON/CIRCLE limite au plan XY/G17."""
    if state.tool_number == 0:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "outil courant absent")
        return None

    work_plane, work_plane_code = iso_writer.machine.get_tool_geometry_work_plane(state.tool_number)
    if work_plane != "XY":
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "CIRCLE CATIA limite au plan XY/G17")
        return None

    tolerance = float(iso_writer.machine.calculation_tolerance)
    if abs(definition.start_z - definition.center_z) > tolerance or abs(definition.center_z - definition.end_z) > tolerance:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, f"geometrie hors plan outil {work_plane_code}")
        return None

    radial_x = definition.start_x - definition.center_x
    radial_y = definition.start_y - definition.center_y
    cw_tangent_x = radial_y
    cw_tangent_y = -radial_x
    ccw_tangent_x = -radial_y
    ccw_tangent_y = radial_x
    cw_alignment = cw_tangent_x * definition.tangent_x + cw_tangent_y * definition.tangent_y
    ccw_alignment = ccw_tangent_x * definition.tangent_x + ccw_tangent_y * definition.tangent_y
    motion_code = iso_writer.machine.circular_move_CW_code if cw_alignment >= ccw_alignment else iso_writer.machine.circular_move_CCW_code

    intersections = geometry_line_circle_intersections_2d(
        definition.center_x, definition.center_y,
        definition.end_x, definition.end_y,
        definition.center_x, definition.center_y,
        definition.radius,
    )
    if not intersections:
        return None

    forward_intersections = [intersection for intersection in intersections if intersection[0] >= -tolerance]
    if forward_intersections:
        selected_intersection = min(forward_intersections, key=lambda intersection: intersection[0])
    else:
        selected_intersection = min(intersections, key=lambda intersection: abs(intersection[0]))

    _, end_x, end_y = selected_intersection
    return TlonArcSolution(
        work_plane_code=work_plane_code,
        motion_code=motion_code,
        center_x=definition.center_x,
        center_y=definition.center_y,
        center_z=definition.center_z,
        end_x=end_x,
        end_y=end_y,
        end_z=definition.center_z,
    )


def solve_tlon_cylndr_definition(definition: TlonArcDefinition, state: WriterState, iso_writer: IsoWriter) -> TlonArcSolution | None:
    """Point d'entree reserve au futur solveur CYLNDR."""
    emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "TLON/CYLNDR a implementer")
    return None


def solve_tlon_definition(definition: TlonArcDefinition, state: WriterState, iso_writer: IsoWriter) -> TlonArcSolution | None:
    """Dispatche la resolution TLON selon la geometrie normalisee."""
    if definition.geometry_kind == "CIRCLE":
        return solve_tlon_circle_xy(definition, state, iso_writer)
    return solve_tlon_cylndr_definition(definition, state, iso_writer)


def emit_tlon_arc(solution: TlonArcSolution, state: WriterState, iso_writer: IsoWriter) -> None:
    """Emet un mouvement circulaire ISO a partir d'une solution TLON."""
    state.position_x = solution.end_x
    state.position_y = solution.end_y
    state.position_z = solution.end_z
    state.motion_mode = MotionMode.WORKING

    iso_writer.circular_move(
        solution.work_plane_code,
        solution.motion_code,
        state.feedrate_value,
        state.feedrate_unit,
        solution.center_x,
        solution.center_y,
        solution.center_z,
        position_x=solution.end_x,
        position_y=solution.end_y,
    )


def h_comment(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter, text_info: str | None = None) -> None:
    """Gere les commandes de type commentaire en les ecrivant telles quelles dans un commentaire ISO."""
    iso_writer.comment(f"{text_info}: {argument_text.upper()}" if text_info else argument_text.upper())

def h_insert(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Gere la commande INSERT en ecrivant le nom du fichier insere comme un commentaire ISO."""
    iso_writer.insert(argument_text)

def h_channel(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Gere la commande CHANNEL en la commentant dans l'ISO."""
    # Exemple accepte : CHANNEL/1
    channel_tokens = csv_tokens(argument_text)
    channel_number = int(channel_tokens[0])
    state.channel_identifier = channel_number
    iso_writer.channel(channel_number)

def h_op_name(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Gere la commande OP_NAME en l'ecrivant comme un commentaire d'operation dans l'ISO, avec un numero de bloc unique."""
    state.bloc_number +=  int(iso_writer.machine.block_increment)
    iso_writer.op_name(state.bloc_number, argument_text)

def h_tprint(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Gere la commande TPRINT en la commentant dans l'ISO et en extrayant le commentaire d'outil pour les changements d'outil."""
    # Exemple accepte : TPRINT/Fraise D1.0 X 3
    tprint_tokens = csv_tokens(argument_text)
    tool_comment = tprint_tokens[0].upper()
    state.tool_comment = tool_comment

def h_tdata(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour le type d'outil et emet les lignes ISO correspondantes si necessaire."""
    # Exemple fraisage : TDATA/MILL,38.000000,38.000000,38.000000,DIAM,1.000000,TYPE,MfgEndMillTool,WEIGHT,,ANGLE,,PITCH,,CORE,0.000000
    # Exemple tournage : TDATA/TURN,0.000000,0.000000,0.000000,QUADRANT,9,RADIUS,0.000000,
    state.previous_tool_type = state.tool_type
    tdata_tokens = csv_tokens(argument_text)
    tool_type = ToolType(str(tdata_tokens[0]))
    state.tool_type = tool_type
    
# TODO: Voir pour degagement avant changement d'outil.
def h_loadtl(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour le numero d'outil et emet les lignes ISO correspondantes si necessaire."""
    # Exemple fraisage : LOADTL/10,ADJUST,1,SPINDL,15915.494300,MILL
    # Exemple tournage : LOADTL/1,ADJUST,9,TURN
    tool_tokens = csv_tokens(argument_text)
    tool_number = int(tool_tokens[0])
    previous_tool_number = state.tool_number

    # En fraisage, un changement d'outil implique d'arreter la broche si elle
    # etait encore consideree active dans l'etat logique courant.
    if state.previous_tool_type == ToolType.MILL and state.spindle_on:
        iso_writer.spindle_stop(previous_tool_number)
        state.spindle_on = False

    state.tool_number = tool_number
    state.previous_tool_type = None
    # Apres un changement d'outil, on suppose que la machine revient a la
    # position de reference de l'outil pour eviter les deplacements rapides inattendus.
    state.position_x = iso_writer.machine.home_tool_x
    state.position_y = iso_writer.machine.home_tool_y
    state.position_z = iso_writer.machine.home_tool_z





    # TODO: Pas assez de verif, a reprendre

    iso_writer.tool_change(state.tool_number, state.tool_comment)





    # TODO: Voir pour la gestion du SPINDL/OFF
def h_spindle(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour la vitesse de broche, l'unite et la direction, et emet les lignes ISO correspondantes si necessaire."""
    # Exemple accepte : SPINDL/3000,CLW
    spindle_tokens = csv_tokens(argument_text)
    spindle_speed = float(spindle_tokens[0])
    spindle_unit = SpindleUnit(spindle_tokens[1])
    spindle_direction = SpindleDirection(spindle_tokens[2])
    state.spindle_speed = spindle_speed
    state.spindle_unit = spindle_unit
    state.spindle_direction = spindle_direction
    state.spindle_on = True
    iso_writer.spindle_start(state.tool_number, spindle_speed, spindle_unit, spindle_direction)

def h_rapid(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Le prochain GOTO utilisera G0."""
    state.motion_mode = MotionMode.RAPID

def h_feedrat(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour l'avance et l'ecrit en ISO si elle a change."""
    # Exemple accepte : FEDRAT/100,MMPM
    feedrate_tokens = csv_tokens(argument_text)
    feedrate_value = float(feedrate_tokens[0])
    feedrate_unit = FeedrateUnit(feedrate_tokens[1])
    # Si l'unite d'avance a change, on l'ajoute a la ligne de mouvement.
    if state.feedrate_value != feedrate_value:
        state.feedrate_value = feedrate_value
    # Si l'unite d'avance a change, on l'ajoute a la ligne de mouvement.
    if state.feedrate_unit != feedrate_unit:
        state.feedrate_unit = feedrate_unit
    state.motion_mode = MotionMode.WORKING

def h_goto(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Deplace la machine selon le mode specifie et les coordonnees fournies."""
    # Exemple accepte : GOTO/100,200,300
    coordinates = csv_floats(argument_text)
    new_x_value = coordinates[0]
    new_y_value = coordinates[1]
    new_z_value = coordinates[2]
    # Utilise une tolerance pour eviter les reemissions dues aux petites variations flottantes.
    tolerance = float(iso_writer.machine.calculation_tolerance)
    x_out = None
    y_out = None
    z_out = None
    # On filtre les petites variations numeriques issues de l'APT afin de ne
    # pas reemettre des blocs ISO pour des ecarts purement flottants.
    # Si une coordonnee a change de plus que la tolerance, on l'ajoute a la ligne de mouvement et on met a jour la position courante.
    if abs(new_x_value - state.position_x) > tolerance:
        state.position_x = new_x_value
        x_out = new_x_value
    if abs(new_y_value - state.position_y) > tolerance:
        state.position_y = new_y_value
        y_out = new_y_value
    if abs(new_z_value - state.position_z) > tolerance:
        state.position_z = new_z_value
        z_out = new_z_value
    # N'emet la ligne de deplacement que si au moins un axe change.
    if x_out is not None or y_out is not None or z_out is not None:
        iso_writer.linear_move(state.tool_number, state.motion_mode, state.toolComp_mode, state.feedrate_value,
                               state.feedrate_unit, position_x=x_out, position_y=y_out, position_z=z_out)

def h_cutcom(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour le mode de compensation d'outil et emet les lignes ISO correspondantes si necessaire."""
    # Exemple accepte : CUTCOM/LEFT
    cutcom_tokens = csv_tokens(argument_text)
    cutcom_mode = ToolComp(cutcom_tokens[0])
    state.toolComp_mode = cutcom_mode

def h_indirv(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Memorise INDIRV/X,Y,Z, soit la tangente du cercle au point de depart."""
    tangent_values = csv_floats(argument_text)
    state.indirv_x = tangent_values[0]
    state.indirv_y = tangent_values[1]
    state.indirv_z = tangent_values[2]

def h_tlon(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Convertit un TLON CATIA en interpolation circulaire ISO."""
    # Definition CATIA V5 prise en charge ici :
    # AUTOPS -
    # INDIRV/ X, Y, Z
    # TLON,GOFWD/ (CIRCLE/ Xc, Yc, Zc,$
    # Rad),ON,(LINE/ Xc, Yc, Zc, Xe, Ye, Ze)
    # TLON,GOFWD/ (CIRCLE/ Xc, Yc, Zc,$
    # Rad),ON,2,INTOF,$
    # (LINE/ Xc, Yc, Zc, Xe, Ye, Ze)
    #
    # X, Y, Z   = composantes de la tangente du cercle au point de depart
    # Xc, Yc, Zc = coordonnees du centre du cercle
    # Rad        = rayon du cercle
    # Xe, Ye, Ze = coordonnees du point final du cercle
    #
    # Dans les APT CATIA V5 traites ici, CIRCLE n'est utilise que pour des
    # deplacements circulaires dans le plan XY (G17).
    #
    # La variante ON,2,INTOF est documentee ici pour conserver la definition
    # CATIA, mais elle n'est pas exploitee par l'implementation actuelle.
    #
    # L'orchestration TLON est volontairement separee en parsing, resolution
    # geometrique et emission ISO pour pouvoir ajouter CYLNDR sans alourdir ce handler.
    tlon_definition = parse_tlon_definition(argument_text, state)
    if tlon_definition is None:
        emit_tlon_not_supported(argument_text, iso_writer)
        return

    tlon_solution = solve_tlon_definition(tlon_definition, state, iso_writer)
    if tlon_solution is None:
        return

    emit_tlon_arc(tlon_solution, state, iso_writer)






def h_fini(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Termine le programme ISO."""
    iso_writer.footer()


def h_default(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Gere les commandes non reconnues en les commentant."""
    iso_writer.comment(f"NON GERE: {apt_keyword}/{argument_text}".strip())


DISPATCH: dict[str, Handler] = {
    

    # Path
    "CHANNEL" : h_channel,

    # Donnees de coupe
    "SPINDL": h_spindle,
    "FEDRAT": h_feedrat,

    
    # Trajectoires
    "RAPID": h_rapid,
    "GOTO": h_goto,
    "CUTCOM": h_cutcom,
    "INDIRV": h_indirv,
    "TLON": h_tlon,
    "END": h_fini,
    # Meta-informations (commentees dans l'ISO)
    #"PARTNO": h_comment(text_info="PART NUMBER"), # TODO: Voir si utile...
    "PART_OPE": partial(h_comment, text_info="PHASE"),
    "PROGRAM": partial(h_comment, text_info="PROGRAMME"),
    "MACHINE": partial(h_comment, text_info="MACHINE"),
    "CATPROCESS": partial(h_comment, text_info="CATPROCESS"),
    "CATPRODUCT": partial(h_comment, text_info="CATPRODUCT"),
    "OP_NAME": h_op_name,
    # Commentaires generaux
    "PPRINT": h_comment,
    # Insertion forcée
    "INSERT": h_insert,
    # Outils
    "TPRINT": h_tprint,
    "TDATA": h_tdata,
    "LOADTL": h_loadtl,
}






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

    # # Securite : si pas de END, on termine quand meme
    # if not iso_writer.out or iso_writer.out[-1] != "%": # Si le programme n'est pas termine, on ajoute un pied de page
    #     if "M30" not in iso_writer.out[-5:]: # Si le pied de page n'est pas deja present, on l'ajoute
    #         iso_writer.footer()

    return iso_writer.out


def convert_file(input_path: str, output_path: str, machine_config: JsonDict, channel_name: str) -> None:
    """Convertit un fichier APT en fichier ISO en utilisant les handlers definis ci-dessus."""
    with open(input_path, "r", encoding="utf-8", errors="replace") as input_file:
        apt_text = input_file.read()
        apt_text = re.sub(r"\$\r?\n", "", apt_text)
        apt_text = re.sub(r" {2,}", " ", apt_text)
        apt_text = re.sub(r"\t", " ", apt_text)
        apt_lines = apt_text.splitlines()

    iso_lines = apt_to_iso_lines(apt_lines, machine_config, channel_name)

    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(iso_lines) + "\n")
