# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
import math

from p03_iso_generator.apt_parser import csv_tokens
from p03_iso_generator.geometric_calculations import (
    ccw_tangent_vector as geometry_ccw_tangent_vector,
    cw_tangent_vector as geometry_cw_tangent_vector,
    project_point_to_plane as geometry_project_point_to_plane,
)
from p03_iso_generator.iso_writer import IsoWriter
from p03_iso_generator.machine_state import WriterState
from p01_machines_config.machine_enums import MotionMode


@dataclass
class HelicalMoveDefinition:
    """Definition normalisee d'un mouvement HELICAL CATIA."""

    center_x: float
    center_y: float
    center_z: float
    tangent_x: float
    tangent_y: float
    tangent_z: float
    axis_i: float
    axis_j: float
    axis_k: float
    pitch: float
    radius: float
    angle: float
    height: float
    round_count: float
    end_x: float
    end_y: float
    end_z: float
    raw_argument_text: str


@dataclass
class HelicalMoveSolution:
    """Resultat geometrique d'un HELICAL pret a etre emis en ISO."""

    work_plane_name: str
    work_plane_code: str
    motion_code: str
    start_z: float
    center_x: float
    center_y: float
    center_z: float
    end_x: float
    end_y: float
    end_z: float


def emit_helical_not_supported(argument_text: str, iso_writer: IsoWriter, reason: str | None = None) -> None:
    """Centralise les messages de non-support pour HELICAL."""
    if reason:
        iso_writer.comment(f"NON GERE: HELICAL/{argument_text} ({reason})")
        return
    iso_writer.comment(f"NON GERE: HELICAL/{argument_text}")


def _rotate_coordinates_around_z(position_x: float, position_y: float, position_z: float, angle_degrees: float) -> tuple[float, float, float]:
    """Applique une rotation aux coordonnees dans le plan XY."""
    angle_radians = math.radians(angle_degrees)
    rotated_x = position_x * math.cos(angle_radians) - position_y * math.sin(angle_radians)
    rotated_y = position_x * math.sin(angle_radians) + position_y * math.cos(angle_radians)
    return rotated_x, rotated_y, position_z


def _transform_helical_definition_to_current_c(definition: HelicalMoveDefinition, position_c: float) -> HelicalMoveDefinition:
    """Transforme les coordonnees/vecteurs APT d'une helice dans le repere ISO courant."""
    center_x, center_y, center_z = _rotate_coordinates_around_z(
        definition.center_x,
        definition.center_y,
        definition.center_z,
        -position_c,
    )
    tangent_x, tangent_y, tangent_z = _rotate_coordinates_around_z(
        definition.tangent_x,
        definition.tangent_y,
        definition.tangent_z,
        -position_c,
    )
    axis_i, axis_j, axis_k = _rotate_coordinates_around_z(
        definition.axis_i,
        definition.axis_j,
        definition.axis_k,
        -position_c,
    )
    end_x, end_y, end_z = _rotate_coordinates_around_z(
        definition.end_x,
        definition.end_y,
        definition.end_z,
        -position_c,
    )

    return HelicalMoveDefinition(
        center_x=center_x,
        center_y=center_y,
        center_z=center_z,
        tangent_x=tangent_x,
        tangent_y=tangent_y,
        tangent_z=tangent_z,
        axis_i=axis_i,
        axis_j=axis_j,
        axis_k=axis_k,
        pitch=definition.pitch,
        radius=definition.radius,
        angle=definition.angle,
        height=definition.height,
        round_count=definition.round_count,
        end_x=end_x,
        end_y=end_y,
        end_z=end_z,
        raw_argument_text=definition.raw_argument_text,
    )


def parse_helical_definition(argument_text: str) -> HelicalMoveDefinition | None:
    """Parse HELICAL/CENTER,...,END,... et retourne une definition normalisee."""
    # Definition CATIA V5 prise en charge ici :
    # HELICAL/CENTER, Xc, Yc, Zc,
    # INDIRV, I, J, K,
    # AXIS, Ia, Ja, Ka,
    # PITCH, Pitch,
    # RADIUS, Rad,
    # ANGLE, Angle,
    # HEIGHT, Height,
    # ROUND, Round,
    # END, Xe, Ye, Ze
    tokens = csv_tokens(argument_text)
    if len(tokens) != 26:
        return None

    if (
        tokens[0].upper() != "CENTER"
        or tokens[4].upper() != "INDIRV"
        or tokens[8].upper() != "AXIS"
        or tokens[12].upper() != "PITCH"
        or tokens[14].upper() != "RADIUS"
        or tokens[16].upper() != "ANGLE"
        or tokens[18].upper() != "HEIGHT"
        or tokens[20].upper() != "ROUND"
        or tokens[22].upper() != "END"
    ):
        return None

    try:
        return HelicalMoveDefinition(
            center_x=float(tokens[1]),
            center_y=float(tokens[2]),
            center_z=float(tokens[3]),
            tangent_x=float(tokens[5]),
            tangent_y=float(tokens[6]),
            tangent_z=float(tokens[7]),
            axis_i=float(tokens[9]),
            axis_j=float(tokens[10]),
            axis_k=float(tokens[11]),
            pitch=float(tokens[13]),
            radius=float(tokens[15]),
            angle=float(tokens[17]),
            height=float(tokens[19]),
            round_count=float(tokens[21]),
            end_x=float(tokens[23]),
            end_y=float(tokens[24]),
            end_z=float(tokens[25]),
            raw_argument_text=argument_text,
        )
    except ValueError:
        return None


def solve_helical_definition(definition: HelicalMoveDefinition, state: WriterState, iso_writer: IsoWriter) -> HelicalMoveSolution | None:
    """Resout un HELICAL si son axe est aligne avec l'axe outil et un plan machine."""
    if not state.tool.number:
        emit_helical_not_supported(definition.raw_argument_text, iso_writer, "outil courant absent")
        return None

    tolerance = float(iso_writer.machine.calculation_tolerance)
    if abs(definition.round_count) > 1.0 + tolerance or abs(definition.angle) > 360.0 + tolerance:
        emit_helical_not_supported(definition.raw_argument_text, iso_writer, "plus d'un tour non supporte")
        return None

    transformed_definition = _transform_helical_definition_to_current_c(definition, state.position_c)

    tool_config = iso_writer.machine.get_required_tool_config(state.tool.number)
    tool_axis_vector = tool_config.get("workplane")
    if not isinstance(tool_axis_vector, (list, tuple)) or len(tool_axis_vector) != 3:
        emit_helical_not_supported(definition.raw_argument_text, iso_writer, "axe outil JSON invalide")
        return None

    axis_i = abs(transformed_definition.axis_i)
    axis_j = abs(transformed_definition.axis_j)
    axis_k = abs(transformed_definition.axis_k)
    tool_axis_i = abs(float(tool_axis_vector[0]))
    tool_axis_j = abs(float(tool_axis_vector[1]))
    tool_axis_k = abs(float(tool_axis_vector[2]))
    if (
        abs(axis_i - tool_axis_i) > tolerance
        or abs(axis_j - tool_axis_j) > tolerance
        or abs(axis_k - tool_axis_k) > tolerance
    ):
        emit_helical_not_supported(definition.raw_argument_text, iso_writer, "axe HELICAL different de l'axe outil")
        return None

    work_plane, work_plane_code = iso_writer.machine.get_tool_geometry_work_plane(state.tool.number)
    axis_matches_work_plane = (
        (work_plane == "XY" and axis_i <= tolerance and axis_j <= tolerance and abs(axis_k - 1.0) <= tolerance)
        or (work_plane == "XZ" and axis_i <= tolerance and abs(axis_j - 1.0) <= tolerance and axis_k <= tolerance)
        or (work_plane == "YZ" and abs(axis_i - 1.0) <= tolerance and axis_j <= tolerance and axis_k <= tolerance)
    )
    if not axis_matches_work_plane:
        emit_helical_not_supported(definition.raw_argument_text, iso_writer, f"axe HELICAL hors plan machine {work_plane_code}")
        return None

    start_u, start_v = geometry_project_point_to_plane(work_plane, state.position_x, state.position_y, state.position_z)
    center_u, center_v = geometry_project_point_to_plane(
        work_plane,
        transformed_definition.center_x,
        transformed_definition.center_y,
        transformed_definition.center_z,
    )
    end_u, end_v = geometry_project_point_to_plane(
        work_plane,
        transformed_definition.end_x,
        transformed_definition.end_y,
        transformed_definition.end_z,
    )

    start_radius = ((start_u - center_u) ** 2 + (start_v - center_v) ** 2) ** 0.5
    end_radius = ((end_u - center_u) ** 2 + (end_v - center_v) ** 2) ** 0.5
    if abs(start_radius - definition.radius) > tolerance or abs(end_radius - definition.radius) > tolerance:
        emit_helical_not_supported(definition.raw_argument_text, iso_writer, "rayon HELICAL incoherent")
        return None

    radial_u = start_u - center_u
    radial_v = start_v - center_v
    if work_plane == "XY":
        tangent_u = transformed_definition.tangent_x
        tangent_v = transformed_definition.tangent_y
    elif work_plane == "XZ":
        tangent_u = transformed_definition.tangent_x
        tangent_v = transformed_definition.tangent_z
    else:
        tangent_u = transformed_definition.tangent_y
        tangent_v = transformed_definition.tangent_z

    cw_tangent_u, cw_tangent_v = geometry_cw_tangent_vector(work_plane, radial_u, radial_v)
    ccw_tangent_u, ccw_tangent_v = geometry_ccw_tangent_vector(work_plane, radial_u, radial_v)
    cw_alignment = cw_tangent_u * tangent_u + cw_tangent_v * tangent_v
    ccw_alignment = ccw_tangent_u * tangent_u + ccw_tangent_v * tangent_v
    motion_code = iso_writer.machine.circular_move_CW_code if cw_alignment >= ccw_alignment else iso_writer.machine.circular_move_CCW_code

    return HelicalMoveSolution(
        work_plane_name=work_plane,
        work_plane_code=work_plane_code,
        motion_code=motion_code,
        start_z=state.position_z,
        center_x=transformed_definition.center_x,
        center_y=transformed_definition.center_y,
        center_z=transformed_definition.center_z,
        end_x=transformed_definition.end_x,
        end_y=transformed_definition.end_y,
        end_z=transformed_definition.end_z,
    )


def emit_helical_move(solution: HelicalMoveSolution, state: WriterState, iso_writer: IsoWriter) -> None:
    """Emet un HELICAL sous forme d'arc ISO avec deplacement simultane sur l'axe hors plan."""
    tolerance = float(iso_writer.machine.calculation_tolerance)
    emit_z = solution.work_plane_name != "XY" and abs(solution.end_z - solution.start_z) > tolerance

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
        position_y=solution.end_y if solution.work_plane_name != "XZ" else None,
        position_z=solution.end_z if emit_z else None,
    )
