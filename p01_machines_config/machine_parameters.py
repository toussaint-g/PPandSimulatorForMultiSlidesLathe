# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import TypeAlias
from p01_machines_config.machine_enums import RotationDirection, ToolComp, ToolType


JsonDict: TypeAlias = dict[str, object]


def normalize_gm_code(code):
    """Normalise un code G/M numerique (ex: G00 -> G0, M06 -> M6)."""
    normalized_code = code.strip().upper()
    prefix = ""
    number = ""
    for character in normalized_code:
        if character.isalpha() and number == "":
            prefix += character
        else:
            number += character
    if not prefix or not number.isdigit():
        return normalized_code
    return f"{prefix}{int(number)}"


def _normalize_axis_vector(workplane_vector: object) -> tuple[float, float, float]:
    """Normalise un vecteur de plan en axe principal, independamment du signe."""
    if not isinstance(workplane_vector, (list, tuple)) or len(workplane_vector) != 3:
        raise ValueError("MachineConfigError: vecteur workplane invalide")

    try:
        vector = tuple(abs(float(component)) for component in workplane_vector)
    except (TypeError, ValueError):
        raise ValueError("MachineConfigError: vecteur workplane invalide")

    if vector == (0.0, 0.0, 1.0):
        return vector
    if vector == (0.0, 1.0, 0.0):
        return vector
    if vector == (1.0, 0.0, 0.0):
        return vector
    raise ValueError("MachineConfigError: vecteur workplane non supporte")


def _extract_tool_change_point_x_for_t0(tool_change_point_x: object) -> float:
    """Extrait la coordonnee X du point de changement outil T0."""
    try:
        return float(tool_change_point_x)
    except (TypeError, ValueError):
        raise ValueError("MachineConfigError: toolchangepointxforT0 invalide")


def _extract_vector(vector: object, field_name: str) -> list[float]:
    """Extrait un vecteur 3D numerique depuis la configuration machine."""
    if not isinstance(vector, (list, tuple)) or len(vector) != 3:
        raise ValueError(f"MachineConfigError: vecteur {field_name} invalide")

    try:
        return [float(component) for component in vector]
    except (TypeError, ValueError):
        raise ValueError(f"MachineConfigError: vecteur {field_name} invalide")


def _get_numbered_config(configs: JsonDict, item_number: int, item_label: str) -> JsonDict | None:
    """Retourne une configuration indexee par numero dans le JSON."""
    item_config = configs.get(str(item_number))
    if item_config is None:
        return None
    if not isinstance(item_config, dict):
        raise ValueError(f"MachineConfigError: configuration {item_label} {item_number} invalide")
    return item_config


def _get_required_numbered_config(configs: JsonDict, item_number: int, item_label: str) -> JsonDict:
    """Retourne une configuration indexee par numero ou leve une erreur."""
    item_config = _get_numbered_config(configs, item_number, item_label)
    if item_config is None:
        raise ValueError(f"MachineConfigError: {item_label} {item_number} introuvable")
    return item_config


@dataclass
class MachineParameters:
    """Regroupe les donnees utiles extraites du JSON machine pour un canal."""

    channel_name: str
    calculation_tolerance: float
    rapidfeedrate: float
    change_tool_time: float
    x_diameter: bool
    rapid_move_code: str
    linear_move_code: str
    circular_move_CW_code: str
    circular_move_CCW_code: str
    timer_code: str
    toolname_prefix: str
    spindle_speed_prefix: str
    program_prefix: str
    feedrate_prefix: str
    feedrate_per_minute: str
    feedrate_per_revolution: str
    coolant_start_code: str | None
    coolant_stop_code: str | None
    endprogram_code: str
    startandendfile_character: str
    block_prefix: str
    block_increment: int
    xy_work_plane_code: str
    xz_work_plane_code: str
    yz_work_plane_code: str
    channel_tool_change_point_x_for_t0: float
    channel_tools: JsonDict
    machine_spindles: JsonDict
    ipartvector: list[float] | None

    def get_spindle_config(self, spindle_number: int) -> JsonDict | None:
        """Retourne la configuration JSON de la broche demandee."""
        return _get_numbered_config(self.machine_spindles, spindle_number, "broche")

    def get_required_spindle_config(self, spindle_number: int) -> JsonDict:
        """Retourne la configuration JSON de la broche ou leve une erreur."""
        return _get_required_numbered_config(self.machine_spindles, spindle_number, "broche")

    def get_spindle_vector(self, spindle_number: int) -> list[float]:
        """Retourne le vecteur d'orientation declare pour la broche."""
        spindle_config = self.get_required_spindle_config(spindle_number)
        return _extract_vector(spindle_config.get("ispindlevector"), "ispindlevector")

    def get_code_for_spindle_c_axis(self, spindle_number: int, c_axis_on: bool) -> str:
        """Retourne le code ISO de passage broche/axe C pour une broche machine."""
        spindle_config = self.get_required_spindle_config(spindle_number)
        code_key = "spindletocaxison" if c_axis_on else "spindletocaxisoff"
        spindle_code = spindle_config.get(code_key)
        if not spindle_code:
            raise ValueError(f"MachineConfigError: code {code_key} absent pour la broche {spindle_number}")
        return normalize_gm_code(str(spindle_code))

    def get_code_for_spindle_brake(self, spindle_number: int, brake_on: bool) -> str:
        """Retourne le code ISO de frein de broche pour une broche machine."""
        spindle_config = self.get_required_spindle_config(spindle_number)
        code_key = "spindlebrakeon" if brake_on else "spindlebrakeoff"
        spindle_code = spindle_config.get(code_key)
        if not spindle_code:
            raise ValueError(f"MachineConfigError: code {code_key} absent pour la broche {spindle_number}")
        return normalize_gm_code(str(spindle_code))

    def get_code_for_turn_spindle(self, spindle_number: int, rotation_direction: RotationDirection | None = None) -> str:
        """Retourne le code ISO pour la mise en rotation d'une broche."""
        spindle_config = self.get_required_spindle_config(spindle_number)
        if rotation_direction == RotationDirection.CLW:
            rotation_code = spindle_config.get("spindleclwstart")
        elif rotation_direction == RotationDirection.CCLW:
            rotation_code = spindle_config.get("spindlecclwstart")
        elif rotation_direction is None:
            rotation_code = spindle_config.get("spindlestop")
        else:
            raise ValueError(f"MachineConfigError: sens de broche '{rotation_direction}' non supporte")

        if not rotation_code:
            raise ValueError(f"MachineConfigError: code de rotation absent pour la broche {spindle_number}")
        return normalize_gm_code(str(rotation_code))

    def get_tool_config(self, tool_number: int) -> JsonDict | None:
        """Retourne la configuration JSON de l'outil pour le canal courant."""
        return _get_numbered_config(self.channel_tools, tool_number, "outil")

    def get_required_tool_config(self, tool_number: int) -> JsonDict:
        """Retourne la configuration JSON de l'outil ou leve une erreur s'il est introuvable."""
        return _get_required_numbered_config(self.channel_tools, tool_number, "outil")

    def get_tool_type(self, tool_number: int) -> ToolType:
        """Retourne le type d'outil declare dans le JSON machine."""
        tool_config = self.get_required_tool_config(tool_number)
        return ToolType(str(tool_config.get("tooltype")).strip().upper())

    def get_tool_change_point_for_c_axis(self, position_c: float) -> tuple[float, float, float]:
        """Retourne le point de changement outil transforme dans le repere machine selon C."""
        tool_change_x = self.channel_tool_change_point_x_for_t0
        tool_change_y = 0.0
        tool_change_z = 0.0
        angle_radians = math.radians(-float(position_c))
        tool_change_x_for_c = tool_change_x * math.cos(angle_radians) - tool_change_y * math.sin(angle_radians)
        tool_change_y_for_c = tool_change_x * math.sin(angle_radians) + tool_change_y * math.cos(angle_radians)
        return tool_change_x_for_c, tool_change_y_for_c, tool_change_z

    def get_tool_change_point_x_for_t0(self) -> float:
        """Retourne la coordonnee X du point de changement outil T0."""
        return self.channel_tool_change_point_x_for_t0

    def get_initial_tool_change_point(self) -> tuple[float, float, float]:
        """Retourne le point de changement outil initial tant qu'aucun outil n'est actif."""
        return self.channel_tool_change_point_x_for_t0, 0.0, 0.0

    def get_code_for_tool_rotation(self, tool_number: int, rotation_direction: RotationDirection | None = None) -> str:
        """Retourne le code ISO pour la mise en rotation d'un outil tournant."""
        tool_config = self.get_required_tool_config(tool_number)
        if rotation_direction == RotationDirection.CLW:
            rotation_code = tool_config.get("toolclwstart")
        elif rotation_direction == RotationDirection.CCLW:
            rotation_code = tool_config.get("toolcclwstart")
        elif rotation_direction is None:
            rotation_code = tool_config.get("toolstop")
        else:
            raise ValueError(f"MachineConfigError: sens de broche '{rotation_direction}' non supporte")

        if not rotation_code:
            raise ValueError(
                f"MachineConfigError: code de rotation absent pour l'outil {tool_number}."
            )
        return normalize_gm_code(str(rotation_code))

    def get_work_plane_code_from_vector(self, workplane_vector: object) -> str:
        """Retourne le code G17/G18/G19 correspondant au vecteur de plan declare dans le JSON."""
        normalized_vector = _normalize_axis_vector(workplane_vector)
        if normalized_vector == (0.0, 0.0, 1.0):
            return self.xy_work_plane_code
        if normalized_vector == (0.0, 1.0, 0.0):
            return self.xz_work_plane_code
        return self.yz_work_plane_code
    
    def get_tool_work_plane_code(self, tool_number: int) -> str:
        """Retourne le code de plan de travail associe a l'outil."""
        tool_config = self.get_required_tool_config(tool_number)
        return self.get_work_plane_code_from_vector(tool_config.get("workplane"))

    def get_tool_geometry_work_plane(self, tool_number: int) -> tuple[str, str]:
        """Retourne le plan geometrique XY/XZ/YZ et son code ISO pour l'outil."""
        work_plane_code = self.get_tool_work_plane_code(tool_number)
        if work_plane_code == self.xy_work_plane_code:
            return "XY", work_plane_code
        if work_plane_code == self.xz_work_plane_code:
            return "XZ", work_plane_code
        if work_plane_code == self.yz_work_plane_code:
            return "YZ", work_plane_code
        raise ValueError(f"MachineConfigError: code plan de travail '{work_plane_code}' non supporte")

    def get_tool_compensation_code_for_tool(self, tool_number: int, tool_compensation: ToolComp) -> str:
        """Retourne le code ISO de compensation outil associe a l'outil et au mode demandes."""
        tool_config = self.get_required_tool_config(tool_number)
        if tool_compensation == ToolComp.LEFT:
            compensation_code = tool_config.get("toolcompleft")
        elif tool_compensation == ToolComp.RIGHT:
            compensation_code = tool_config.get("toolcompright")
        elif tool_compensation == ToolComp.OFF:
            compensation_code = tool_config.get("toolcompoff")
        else:
            raise ValueError(
                f"MachineConfigError: mode de compensation outil '{tool_compensation}' non supporte"
            )

        if not compensation_code:
            raise ValueError(
                f"MachineConfigError: code de compensation absent pour l'outil {tool_number} dans le canal {self.channel_name}"
            )
        return normalize_gm_code(str(compensation_code))

    @classmethod
    def from_machine_config(cls, machine_config: JsonDict) -> "MachineParameters":
        """Construit les parametres a partir du premier canal disponible."""
        try:
            channel_name = next(iter(machine_config["listofchannels"]))
        except StopIteration:
            raise ValueError("MachineConfigError: aucun canal n'est defini dans le fichier JSON")
        return cls.from_config(machine_config, channel_name)

    @classmethod
    def from_config(machine_parameters_builder, machine_config: JsonDict, channel_name: str) -> "MachineParameters":
        """Construit les parametres machine/canal a partir du JSON charge."""
        try:
            machine_informations: JsonDict = machine_config["machineinformations"]  # type: ignore[assignment]
            spindles_list: JsonDict = machine_config["listofspindles"]  # type: ignore[assignment]
            channels_list: JsonDict = machine_config["listofchannels"]  # type: ignore[assignment]
            channel_config: JsonDict = channels_list[channel_name]  # type: ignore[index]
            channel_tool_change_point_x_for_t0 = _extract_tool_change_point_x_for_t0(
                channel_config["toolchangepointxforT0"]
            )

            coolant_start_code = machine_informations.get("coolantstart")
            coolant_stop_code = machine_informations.get("coolantstop")

            return machine_parameters_builder(
                channel_name=channel_name,
                calculation_tolerance=machine_config["calculationtolerance"],
                rapidfeedrate=machine_informations["rapidfeedrate"],
                change_tool_time=machine_informations["changetooltime"],
                x_diameter=machine_informations["xdiameter"],
                rapid_move_code=normalize_gm_code(machine_informations["rapidmove"]),
                linear_move_code=normalize_gm_code(machine_informations["linearmove"]),
                circular_move_CW_code=normalize_gm_code(machine_informations["circularmoveCW"]),
                circular_move_CCW_code=normalize_gm_code(machine_informations["circularmoveCCW"]),
                timer_code=normalize_gm_code(machine_informations["timer"]),
                toolname_prefix=machine_informations["toolnameprefix"],
                spindle_speed_prefix=machine_informations["spindlespeedprefix"],
                program_prefix=machine_informations["programprefix"],
                feedrate_prefix=machine_informations["feedrateprefix"],
                feedrate_per_minute=normalize_gm_code(machine_informations["feedrateperminute"]),
                feedrate_per_revolution=normalize_gm_code(machine_informations["feedrateperrevolution"]),
                coolant_start_code=normalize_gm_code(coolant_start_code),
                coolant_stop_code=normalize_gm_code(coolant_stop_code),
                endprogram_code=normalize_gm_code(machine_informations["endprogram"]),
                startandendfile_character=machine_informations["startandendfilecharacter"],
                block_prefix=machine_informations["blockprefix"],
                block_increment=machine_informations["blockincrement"],
                xy_work_plane_code=normalize_gm_code(machine_informations["xyworkplane"]),
                xz_work_plane_code=normalize_gm_code(machine_informations["xzworkplane"]),
                yz_work_plane_code=normalize_gm_code(machine_informations["yzworkplane"]),
                channel_tool_change_point_x_for_t0=channel_tool_change_point_x_for_t0,
                channel_tools=channel_config["listoftools"],
                machine_spindles=spindles_list,
                ipartvector=machine_informations.get("ipartvector"),
            )
        except KeyError:
            raise ValueError("MachineConfigError: une cle est absente dans le fichier JSON")
