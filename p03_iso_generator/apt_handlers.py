# -*- coding: utf-8 -*-

from __future__ import annotations

import math
from functools import partial
from typing import Callable

from p01_machines_config.machine_enums import FeedrateUnit, MotionMode, RotationDirection, RotationUnit, ToolComp, ToolType, AxisOfRotation
from p03_iso_generator.apt_parser import csv_floats, csv_tokens
from p03_iso_generator.helical import emit_helical_move, emit_helical_not_supported, parse_helical_definition, solve_helical_definition
from p03_iso_generator.iso_writer import IsoWriter
from p03_iso_generator.machine_state import SpindleSelection, ToolSelection, WriterState
from p03_iso_generator.tlon import emit_tlon_arc, emit_tlon_not_supported, parse_tlon_definition, solve_tlon_definition


Handler = Callable[[str, str, WriterState, IsoWriter], None]


def _normalize_angle_0_360(angle_degrees: float) -> float:
    """Normalise un angle en degres dans l'intervalle [0, 360[."""
    return angle_degrees % 360.0


def _vector_xy_angle_degrees(vector_i: float, vector_j: float) -> float:
    """Retourne l'angle XY d'un vecteur par rapport a +X."""
    return math.degrees(math.atan2(vector_j, vector_i))


def _get_tool_k_vector(state: WriterState, iso_writer: IsoWriter) -> tuple[float, float, float]:
    """Retourne le ktoolvector de l'outil courant."""
    tool_config = iso_writer.machine.get_required_tool_config(state.tool_number)
    tool_vector = tool_config.get("ktoolvector")
    if not isinstance(tool_vector, (list, tuple)) or len(tool_vector) != 3:
        raise ValueError(f"MachineConfigError: ktoolvector absent ou invalide pour l'outil {state.tool_number}")
    tool_i = float(tool_vector[0])
    tool_j = float(tool_vector[1])
    tool_k = float(tool_vector[2])
    if (tool_i, tool_j, tool_k) in ((0.0, 1.0, 0.0), (0.0, -1.0, 0.0)):
        raise ValueError(f"MachineConfigError: ktoolvector aligne sur Y non supporte pour l'outil {state.tool_number}")
    return tool_i, tool_j, tool_k


def _validate_spindle_vector(spindle_vector: object, spindle_number: int) -> tuple[float, float, float]:
    """Valide le ispindlevector de la broche active."""
    if not isinstance(spindle_vector, (list, tuple)) or len(spindle_vector) != 3:
        raise ValueError(
            f"MachineConfigError: ispindlevector absent ou invalide pour la broche {spindle_number}"
        )

    try:
        path_i = float(spindle_vector[0])
        path_j = float(spindle_vector[1])
        path_k = float(spindle_vector[2])
    except (TypeError, ValueError):
        raise ValueError(f"MachineConfigError: ispindlevector invalide pour la broche {spindle_number}")

    if (path_i, path_j, path_k) not in ((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)):
        raise ValueError(f"MachineConfigError: ispindlevector non supporte pour la broche {spindle_number}")
    return path_i, path_j, path_k


def _get_active_spindle_vector(state: WriterState) -> tuple[float, float, float]:
    """Retourne le ispindlevector de la broche active declaree par SPINDL_NAME."""
    if (
        state.spindle_number is None
        or state.spindle_vector_i is None
        or state.spindle_vector_j is None
        or state.spindle_vector_k is None
    ):
        raise ValueError("MachineConfigError: SPINDL_NAME absent avant un mouvement de fraisage")
    return state.spindle_vector_i, state.spindle_vector_j, state.spindle_vector_k


def _is_milling_tool(state: WriterState, iso_writer: IsoWriter) -> bool:
    """Retourne True si l'outil courant est declare en fraisage dans la config machine."""
    return iso_writer.machine.get_tool_type(state.tool_number) == ToolType.MILL


def _compute_c_axis_from_ijk(
    apt_i: float,
    apt_j: float,
    apt_k: float,
    tool_i: float,
    tool_j: float,
    path_i: float,
    path_j: float,
    tolerance: float,
) -> float | None:
    """Calcule C depuis le vecteur APT, relativement au ispindlevector et ktoolvector courants."""
    apt_has_xy_component = abs(apt_i) > tolerance or abs(apt_j) > tolerance
    apt_has_z_component = abs(apt_k) > tolerance

    if not apt_has_xy_component:
        return 0.0
    if apt_has_z_component:
        return None
    if abs(tool_i) <= tolerance and abs(tool_j) <= tolerance:
        return None

    apt_angle = _vector_xy_angle_degrees(apt_i, apt_j)
    path_angle = _vector_xy_angle_degrees(path_i, path_j)
    tool_angle = _vector_xy_angle_degrees(tool_i, tool_j)
    return _normalize_angle_0_360(apt_angle + path_angle - tool_angle)


def _rotate_coordinates_around_z(position_x: float, position_y: float, position_z: float, angle_degrees: float) -> tuple[float, float, float]:
    """Applique une rotation aux coordonnees APT dans le plan XY."""
    angle_radians = math.radians(angle_degrees)
    rotated_x = position_x * math.cos(angle_radians) - position_y * math.sin(angle_radians)
    rotated_y = position_x * math.sin(angle_radians) + position_y * math.cos(angle_radians)
    return rotated_x, rotated_y, position_z


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


def h_loadtl(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour le numero d'outil et emet les lignes ISO correspondantes si necessaire."""
    # Exemple fraisage : LOADTL/10,ADJUST,1,SPINDL,15915.494300,MILL
    # Exemple tournage : LOADTL/1,ADJUST,9,TURN
    tool_tokens = csv_tokens(argument_text)
    tool_number = int(tool_tokens[0])
    tool_type = ToolType(str(tool_tokens[-1]).strip().upper())
    state.tool_number = tool_number
    state.tool_type = tool_type
    state.linked_spindle_number = iso_writer.machine.get_tool_linked_spindle(tool_number)

    # On verifie que le type d'outil dans l'APT correspond a celui declare dans la config machine pour eviter les incoherences.
    json_tool_type = iso_writer.machine.get_tool_type(state.tool_number)
    if json_tool_type != state.tool_type:
        raise ValueError(
            f"MachineConfigError: type outil LOADTL {state.tool_type.value} different du JSON {json_tool_type.value} pour l'outil {state.tool_number}"
        )
    # Avant le changement d'outil, on deplace la machine au point de changement d'outil pour eviter les collisions.
    state.position_x = iso_writer.machine.get_tool_change_point_x_for_t0()
    # Traitement du tool change
    state.tool_change_processing = True


def h_spindle_name(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour le numero de broche."""
    # Exemple accepte : SPINDL_NAME/NAME,BP_PATH1,NUMB,1
    spindle_tokens = csv_tokens(argument_text)
    spindle_number = int(spindle_tokens[3])
    spindle_vector = iso_writer.machine.get_spindle_vector(spindle_number)
    spindle_i, spindle_j, spindle_k = _validate_spindle_vector(spindle_vector, spindle_number)
    state.spindle_number = spindle_number
    state.spindle_vector_i = spindle_i
    state.spindle_vector_j = spindle_j
    state.spindle_vector_k = spindle_k

    # Verification de la coherence entre la broche declaree et l'outil lie a cette broche.
    if state.linked_spindle_number != state.spindle_number:
        raise ValueError(
            f"ATTENTION: broche {state.spindle_number} selectionnee dans CATIA alors que l'outil {state.tool_number} est lie a la broche {state.linked_spindle_number}"
        )
    










def h_spindle(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour la vitesse de broche, l'unite et la direction, et emet les lignes ISO correspondantes si necessaire."""
    # Exemple accepte : SPINDL/3000,CLW
    rotation_tokens = csv_tokens(argument_text)
    rotation_speed = float(rotation_tokens[0])
    rotation_unit = RotationUnit(rotation_tokens[1])
    rotation_direction = RotationDirection(rotation_tokens[2])
    state.rotation_speed = rotation_speed
    state.rotation_unit = rotation_unit
    state.rotation_direction = rotation_direction

    # SPINDL finalise l'etat outil/broche et declenche l'emission ISO.
    tool_update = iso_writer.apply_tool_update(
        ToolSelection.from_writer_state(state),
        SpindleSelection.from_writer_state(state),
        state.position_x,
        state.position_c,
        state.tool_change_processing,
            )

    if tool_update.position_c is not None:
        state.position_c = tool_update.position_c
    if tool_update.position_y is not None:
        state.position_y = tool_update.position_y

    state.tool_change_processing = False


















def h_rapid(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Le prochain GOTO utilisera G0."""
    state.motion_mode = MotionMode.RAPID


def h_feedrat(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour l'avance et l'ecrit en ISO si elle a change."""
    # Exemple accepte : FEDRAT/100,MMPM
    feedrate_tokens = csv_tokens(argument_text)
    feedrate_value = float(feedrate_tokens[0])
    feedrate_unit = FeedrateUnit(feedrate_tokens[1])

    # Si l'avance a change, on l'ajoute a la ligne de mouvement.
    if state.feedrate_value != feedrate_value:
        state.feedrate_value = feedrate_value

    # Si l'unite d'avance a change, on l'ajoute a la ligne de mouvement.
    if state.feedrate_unit != feedrate_unit:
        state.feedrate_unit = feedrate_unit

    state.motion_mode = MotionMode.WORKING


def h_goto(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Deplace la machine selon le mode specifie et les coordonnees fournies."""
    # Exemple accepte : GOTO/1.45000,0.10000,0.01921,0.000000,0.000000,-1.000000
    coordinates = csv_floats(argument_text)
    new_x_value = coordinates[0]
    new_y_value = coordinates[1]
    new_z_value = coordinates[2]
    new_i_value = coordinates[3]
    new_j_value = coordinates[4]
    new_k_value = coordinates[5]

    # Utilise une tolerance pour eviter les reemissions dues aux petites variations flottantes.
    tolerance = float(iso_writer.machine.calculation_tolerance)
    x_out = None
    y_out = None
    z_out = None
    c_out = None

    if _is_milling_tool(state, iso_writer):
        tool_i_value, tool_j_value, _tool_k_value = _get_tool_k_vector(state, iso_writer)
        path_i_value, path_j_value, _path_k_value = _get_active_spindle_vector(state)
        new_c_value = _compute_c_axis_from_ijk(
            new_i_value,
            new_j_value,
            new_k_value,
            tool_i_value,
            tool_j_value,
            path_i_value,
            path_j_value,
            tolerance,
        )
        if new_c_value is None:
            iso_writer.comment(
                "ERREUR: VECTEUR IJK INACCESSIBLE AVEC AXE C SEUL "
                f"I{new_i_value} J{new_j_value} K{new_k_value}"
            )
            return
        new_x_value, new_y_value, new_z_value = _rotate_coordinates_around_z(
            new_x_value,
            new_y_value,
            new_z_value,
            -new_c_value,
        )
    else:
        new_c_value = 0.0

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
    if abs(new_c_value - state.position_c) > tolerance:
        state.position_c = new_c_value
        c_out = new_c_value

    # N'emet la ligne de deplacement que si au moins un axe change.
    if x_out is not None or y_out is not None or z_out is not None or c_out is not None:
        iso_writer.linear_move(state.tool_number, state.motion_mode, state.toolComp_mode, state.feedrate_value,
                               state.feedrate_unit, position_x=x_out, position_y=y_out, position_z=z_out,
                               position_c=c_out)

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
    # L'orchestration TLON est volontairement separee en parsing, resolution
    # geometrique et emission ISO pour garder le traitement CIRCLE/CYLNDR lisible.
    tlon_definition = parse_tlon_definition(argument_text, state)

    if tlon_definition is None:
        emit_tlon_not_supported(argument_text, iso_writer)
        return
    tlon_solution = solve_tlon_definition(tlon_definition, state, iso_writer)

    if tlon_solution is None:
        return
    
    emit_tlon_arc(tlon_solution, state, iso_writer)


def h_helical(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Convertit un HELICAL CATIA en interpolation circulaire ISO avec axe hors plan."""
    helical_definition = parse_helical_definition(argument_text)

    if helical_definition is None:
        emit_helical_not_supported(argument_text, iso_writer)
        return
    helical_solution = solve_helical_definition(helical_definition, state, iso_writer)

    if helical_solution is None:
        return
    
    emit_helical_move(helical_solution, state, iso_writer)











# TODO: a finaliser apres verification des mouvements en axe C.
def h_rotabl(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Met a jour le mode de compensation d'outil et emet les lignes ISO correspondantes si necessaire."""
    # Exemple accepte : ROTABL/180.000000,CLW,CAXIS
    rotabl_tokens = csv_tokens(argument_text)
    rotabl_amount = float(rotabl_tokens[0])
    rotabl_direction = RotationDirection(rotabl_tokens[1])
    rotabl_axis = AxisOfRotation(rotabl_tokens[2])

    # Si CAXIS, on traite sinon, message d'erreur.
    if rotabl_axis == AxisOfRotation.CAXIS and state.tool_type == ToolType.MILL:
        # On applique la rotation a l'axe C en fonction du sens de rotation et de l'angle de rotation.
        if rotabl_direction == RotationDirection.CLW:
            state.position_c += rotabl_amount
        else:
            state.position_c -= rotabl_amount
    else:
        iso_writer.comment(f"ROTABL non supporte pour axe {rotabl_axis.value}")
        return
    














def h_fini(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Termine le programme ISO."""
    iso_writer.footer(state.tool_number, state.spindle_number)


def h_default(apt_keyword: str, argument_text: str, state: WriterState, iso_writer: IsoWriter) -> None:
    """Gere les commandes non reconnues en les commentant."""
    iso_writer.comment(f"NON GERE: {apt_keyword}/{argument_text}".strip())


DISPATCH: dict[str, Handler] = {
    # Path
    "CHANNEL" : h_channel,
    # Broches
    "SPINDL_NAME": h_spindle_name,
    "SPINDL": h_spindle,
    # Outils
    "TPRINT": h_tprint,
    "LOADTL": h_loadtl,
    # Donnees de coupe
    "FEDRAT": h_feedrat,
    # Trajectoires lineaires
    "RAPID": h_rapid,
    "GOTO": h_goto,
    # Trajectoires circulaires
    "INDIRV": h_indirv,
    "TLON": h_tlon,
    "HELICAL": h_helical,
    # Rotation d'axes
    "ROTABL": h_rotabl,
    # Compensation
    "CUTCOM": h_cutcom,
    # Meta-informations (commentees dans l'ISO)
    "PART_OPE": partial(h_comment, text_info="PHASE"),
    "PROGRAM": partial(h_comment, text_info="PROGRAMME"),
    "MACHINE": partial(h_comment, text_info="MACHINE"),
    "CATPROCESS": partial(h_comment, text_info="CATPROCESS"),
    "CATPRODUCT": partial(h_comment, text_info="CATPRODUCT"),
    "OP_NAME": h_op_name,
    # Commentaires generaux
    "PPRINT": h_comment,
    # Insertions forcees
    "INSERT": h_insert,
    # Programme
    "END": h_fini,
}
