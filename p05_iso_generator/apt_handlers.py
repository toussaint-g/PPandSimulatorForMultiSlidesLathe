# -*- coding: utf-8 -*-

from __future__ import annotations

from functools import partial
from typing import Callable

from p02_machines_config.machine_enums import FeedrateUnit, MotionMode, SpindleDirection, SpindleUnit, ToolComp, ToolType
from p05_iso_generator.apt_parser import csv_floats, csv_tokens
from p05_iso_generator.helical import emit_helical_move, emit_helical_not_supported, parse_helical_definition, solve_helical_definition
from p05_iso_generator.iso_writer import IsoWriter
from p05_iso_generator.machine_state import WriterState
from p05_iso_generator.tlon import emit_tlon_arc, emit_tlon_not_supported, parse_tlon_definition, solve_tlon_definition


Handler = Callable[[str, str, WriterState, IsoWriter], None]


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
    "HELICAL": h_helical,
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
