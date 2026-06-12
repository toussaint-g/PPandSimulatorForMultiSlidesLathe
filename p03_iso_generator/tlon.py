# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
import math
import re

from app_errors import unmanaged_diagnostic
from p01_machines_config.machine_enums import MotionMode
from p03_iso_generator.apt_parser import csv_floats
from p03_iso_generator.geometric_calculations import (
    build_point_from_plane as geometry_build_point_from_plane,
    ccw_tangent_vector as geometry_ccw_tangent_vector,
    cw_tangent_vector as geometry_cw_tangent_vector,
    line_circle_intersections_2d as geometry_line_circle_intersections_2d,
    project_point_to_plane as geometry_project_point_to_plane,
)
from p03_iso_generator.iso_writer import IsoWriter
from p03_iso_generator.machine_state import WriterState


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

    work_plane_name: str
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
    iso_writer.comment(unmanaged_diagnostic("TLON", argument_text, reason))


def _rotate_coordinates_around_z(position_x: float, position_y: float, position_z: float, angle_degrees: float) -> tuple[float, float, float]:
    """Applique une rotation aux coordonnees dans le plan XY."""
    angle_radians = math.radians(angle_degrees)
    rotated_x = position_x * math.cos(angle_radians) - position_y * math.sin(angle_radians)
    rotated_y = position_x * math.sin(angle_radians) + position_y * math.cos(angle_radians)
    return rotated_x, rotated_y, position_z


def _transform_tlon_definition_to_current_c(definition: TlonArcDefinition, position_c: float) -> TlonArcDefinition:
    """Transforme les coordonnees/vecteurs APT d'un arc dans le repere ISO courant."""
    tangent_x, tangent_y, tangent_z = _rotate_coordinates_around_z(
        definition.tangent_x,
        definition.tangent_y,
        definition.tangent_z,
        -position_c,
    )
    center_x, center_y, center_z = _rotate_coordinates_around_z(
        definition.center_x,
        definition.center_y,
        definition.center_z,
        -position_c,
    )
    end_x, end_y, end_z = _rotate_coordinates_around_z(
        definition.end_x,
        definition.end_y,
        definition.end_z,
        -position_c,
    )

    axis_u = definition.axis_u
    axis_v = definition.axis_v
    axis_w = definition.axis_w
    if axis_u is not None and axis_v is not None and axis_w is not None:
        axis_u, axis_v, axis_w = _rotate_coordinates_around_z(axis_u, axis_v, axis_w, -position_c)

    return TlonArcDefinition(
        geometry_kind=definition.geometry_kind,
        start_x=definition.start_x,
        start_y=definition.start_y,
        start_z=definition.start_z,
        tangent_x=tangent_x,
        tangent_y=tangent_y,
        tangent_z=tangent_z,
        center_x=center_x,
        center_y=center_y,
        center_z=center_z,
        radius=definition.radius,
        end_x=end_x,
        end_y=end_y,
        end_z=end_z,
        raw_argument_text=definition.raw_argument_text,
        axis_u=axis_u,
        axis_v=axis_v,
        axis_w=axis_w,
    )


def parse_tlon_circle_definition(argument_text: str, state: WriterState) -> TlonArcDefinition | None:
    """Parse la variante CATIA TLON basee sur CIRCLE et retourne une definition normalisee."""
    # Definition CATIA V5 prise en charge ici :
    # AUTOPS -
    # INDIRV/ X, Y, Z
    # TLON,GOFWD/ (CIRCLE/ Xc, Yc, Zc,$
    # Rad),ON,(LINE/ Xc, Yc, Zc, Xe, Ye, Ze)
    # TLON,GOFWD/ (CIRCLE/ Xc, Yc, Zc,$
    # Rad),ON,2,INTOF,$
    # (LINE/ Xc, Yc, Zc, Xe, Ye, Ze)
    #
    # X, Y, Z    = composantes de la tangente du cercle au point de depart
    # Xc, Yc, Zc = coordonnees du centre du cercle
    # Rad        = rayon du cercle
    # Xe, Ye, Ze = coordonnees du point final du cercle
    #
    # Dans les APT CATIA V5 traites ici, CIRCLE n'est utilise que pour des
    # deplacements circulaires dans le plan XY (G17).
    #
    # La variante ON,2,INTOF est acceptee au parsing. Les deux parametres
    # supplementaires sont ignores pour l'instant, mais ils sont conserves
    # dans la documentation car ils pourront etre exploites plus tard.
    geometry_match = re.search(
        r"\(CIRCLE/\s*([^)]+?)\s*\),\s*ON(?:\s*,\s*2\s*,\s*INTOF)?\s*,\s*\(LINE/\s*([^)]+?)\s*\)",
        argument_text,
        re.IGNORECASE,
    )
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
    # Definition CATIA V5 prise en charge ici :
    # PSIS/(PLANE/(POINT/ x, y, z),PERPTO,$
    # (VECTOR/ u, v, w))
    # INDIRV/ X, Y, Z
    # TLON,GOFWD/ (CYLNDR / Xc, Yc, Zc,$
    # Ua, Va, Wa, Rad), ON,$
    # (PLANE/PERPTO,$
    # (PLANE/(POINT/Xc,Yc,Zc),PERPTO,$
    # (VECTOR/Ua,Va,Wa)),$
    # (POINT/Xc,Yc,Zc),$
    # (POINT/Xe,Ye,Ze))
    #
    # x, y, z    = coordonnees de la pointe-outil
    # u, v, w    = composantes de l'axe du cercle
    # X, Y, Z    = composantes de la tangente du cercle au point de depart
    # Xc, Yc, Zc = coordonnees du centre du cercle
    # Ua, Va, Wa = composantes de l'axe du cercle
    # Rad        = rayon du cercle
    # Xe, Ye, Ze = coordonnees du point final
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


def _get_work_plane_projection_data(definition: TlonArcDefinition, work_plane: str, work_plane_code: str, iso_writer: IsoWriter) -> tuple[float, float, float, float, float, float, float, float, float] | None:
    """Retourne les donnees 2D utiles au calcul d'arc dans le plan machine demande."""
    tolerance = float(iso_writer.machine.calculation_tolerance)

    if work_plane == "XY":
        constant_value = definition.center_z
        tangent_u = definition.tangent_x
        tangent_v = definition.tangent_y
        if abs(definition.start_z - definition.center_z) > tolerance or abs(definition.center_z - definition.end_z) > tolerance:
            emit_tlon_not_supported(definition.raw_argument_text, iso_writer, f"geometrie hors plan outil {work_plane_code}")
            return None
    elif work_plane == "XZ":
        constant_value = definition.center_y
        tangent_u = definition.tangent_x
        tangent_v = definition.tangent_z
        if abs(definition.start_y - definition.center_y) > tolerance or abs(definition.center_y - definition.end_y) > tolerance:
            emit_tlon_not_supported(definition.raw_argument_text, iso_writer, f"geometrie hors plan outil {work_plane_code}")
            return None
    else:
        constant_value = definition.center_x
        tangent_u = definition.tangent_y
        tangent_v = definition.tangent_z
        if abs(definition.start_x - definition.center_x) > tolerance or abs(definition.center_x - definition.end_x) > tolerance:
            emit_tlon_not_supported(definition.raw_argument_text, iso_writer, f"geometrie hors plan outil {work_plane_code}")
            return None

    start_u, start_v = geometry_project_point_to_plane(work_plane, definition.start_x, definition.start_y, definition.start_z)
    center_u, center_v = geometry_project_point_to_plane(work_plane, definition.center_x, definition.center_y, definition.center_z)
    end_u, end_v = geometry_project_point_to_plane(work_plane, definition.end_x, definition.end_y, definition.end_z)
    return constant_value, tangent_u, tangent_v, start_u, start_v, center_u, center_v, end_u, end_v


def _solve_tlon_arc_in_machine_plane(definition: TlonArcDefinition, work_plane: str, work_plane_code: str, iso_writer: IsoWriter) -> TlonArcSolution | None:
    """Resout un TLON dans un plan machine principal deja valide."""
    projection_data = _get_work_plane_projection_data(definition, work_plane, work_plane_code, iso_writer)
    if projection_data is None:
        return None

    constant_value, tangent_u, tangent_v, start_u, start_v, center_u, center_v, end_u, end_v = projection_data
    radial_u = start_u - center_u
    radial_v = start_v - center_v
    cw_tangent_u, cw_tangent_v = geometry_cw_tangent_vector(work_plane, radial_u, radial_v)
    ccw_tangent_u, ccw_tangent_v = geometry_ccw_tangent_vector(work_plane, radial_u, radial_v)
    cw_alignment = cw_tangent_u * tangent_u + cw_tangent_v * tangent_v
    ccw_alignment = ccw_tangent_u * tangent_u + ccw_tangent_v * tangent_v
    motion_code = iso_writer.machine.circular_move_CW_code if cw_alignment >= ccw_alignment else iso_writer.machine.circular_move_CCW_code

    intersections = geometry_line_circle_intersections_2d(
        center_u, center_v,
        end_u, end_v,
        center_u, center_v,
        definition.radius,
    )
    if not intersections:
        return None

    tolerance = float(iso_writer.machine.calculation_tolerance)
    forward_intersections = [intersection for intersection in intersections if intersection[0] >= -tolerance]
    if forward_intersections:
        selected_intersection = min(forward_intersections, key=lambda intersection: intersection[0])
    else:
        selected_intersection = min(intersections, key=lambda intersection: abs(intersection[0]))

    _, solved_end_u, solved_end_v = selected_intersection
    solved_end_x, solved_end_y, solved_end_z = geometry_build_point_from_plane(work_plane, solved_end_u, solved_end_v, constant_value)
    return TlonArcSolution(
        work_plane_name=work_plane,
        work_plane_code=work_plane_code,
        motion_code=motion_code,
        center_x=definition.center_x,
        center_y=definition.center_y,
        center_z=definition.center_z,
        end_x=solved_end_x,
        end_y=solved_end_y,
        end_z=solved_end_z,
    )


def solve_tlon_circle_xy(definition: TlonArcDefinition, state: WriterState, iso_writer: IsoWriter) -> TlonArcSolution | None:
    """Resout geometriquement un TLON/CIRCLE dans le plan outil courant."""
    if not state.tool.number:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "outil courant absent")
        return None

    work_plane, work_plane_code = iso_writer.machine.get_tool_geometry_work_plane(state.tool.number)
    transformed_definition = _transform_tlon_definition_to_current_c(definition, state.position_c)
    return _solve_tlon_arc_in_machine_plane(transformed_definition, work_plane, work_plane_code, iso_writer)


def solve_tlon_cylndr_definition(definition: TlonArcDefinition, state: WriterState, iso_writer: IsoWriter) -> TlonArcSolution | None:
    """Resout un TLON/CYLNDR si l'axe du cylindre coincide avec un plan machine."""
    if not state.tool.number:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "outil courant absent")
        return None
    if definition.axis_u is None or definition.axis_v is None or definition.axis_w is None:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "axe CYLNDR absent")
        return None

    transformed_definition = _transform_tlon_definition_to_current_c(definition, state.position_c)

    work_plane, work_plane_code = iso_writer.machine.get_tool_geometry_work_plane(state.tool.number)
    tolerance = float(iso_writer.machine.calculation_tolerance)
    tool_config = iso_writer.machine.get_required_tool_config(state.tool.number)
    tool_axis_vector = tool_config.get("workplane")
    if not isinstance(tool_axis_vector, (list, tuple)) or len(tool_axis_vector) != 3:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "axe outil JSON invalide")
        return None

    if (
        transformed_definition.axis_u is None
        or transformed_definition.axis_v is None
        or transformed_definition.axis_w is None
    ):
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "axe CYLNDR absent")
        return None

    axis_u = abs(transformed_definition.axis_u)
    axis_v = abs(transformed_definition.axis_v)
    axis_w = abs(transformed_definition.axis_w)
    tool_axis_u = abs(float(tool_axis_vector[0]))
    tool_axis_v = abs(float(tool_axis_vector[1]))
    tool_axis_w = abs(float(tool_axis_vector[2]))

    if abs(axis_u - tool_axis_u) > tolerance or abs(axis_v - tool_axis_v) > tolerance or abs(axis_w - tool_axis_w) > tolerance:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, "axe CYLNDR different de l'axe outil")
        return None

    axis_matches_work_plane = (
        (work_plane == "XY" and abs(axis_u) <= tolerance and abs(axis_v) <= tolerance and abs(axis_w - 1.0) <= tolerance)
        or (work_plane == "XZ" and abs(axis_u) <= tolerance and abs(axis_v - 1.0) <= tolerance and abs(axis_w) <= tolerance)
        or (work_plane == "YZ" and abs(axis_u - 1.0) <= tolerance and abs(axis_v) <= tolerance and abs(axis_w) <= tolerance)
    )
    if not axis_matches_work_plane:
        emit_tlon_not_supported(definition.raw_argument_text, iso_writer, f"axe CYLNDR hors plan machine {work_plane_code}")
        return None

    return _solve_tlon_arc_in_machine_plane(transformed_definition, work_plane, work_plane_code, iso_writer)


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
        position_y=solution.end_y if solution.work_plane_name != "XZ" else None,
        position_z=solution.end_z if solution.work_plane_name != "XY" else None,
    )
