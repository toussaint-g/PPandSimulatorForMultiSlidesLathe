# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias
from p01_machines_config.machine_enums import SpindleDirection, ToolComp


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


def _extract_home_tool_coordinates(home_tool: object) -> tuple[float, float, float]:
    """Extrait les coordonnees home tool depuis une liste [x, y, z]."""
    if isinstance(home_tool, (list, tuple)) and len(home_tool) == 3:
        try:
            return float(home_tool[0]), float(home_tool[1]), float(home_tool[2])
        except (TypeError, ValueError):
            raise ValueError("MachineConfigError: hometool invalide")

    raise ValueError("MachineConfigError: hometool invalide")


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
    home_tool_x: float
    home_tool_y: float
    home_tool_z: float
    channel_tools: list[JsonDict]
    ipartvector: list[float] | None
    jpartvector: list[float] | None
    kpartvector: list[float] | None
    ipathvector: list[float] | None
    jpathvector: list[float] | None
    kpathvector: list[float] | None

    def get_tool_config(self, tool_number: int) -> JsonDict | None:
        """Retourne la configuration JSON de l'outil pour le canal courant."""
        for tool_config in self.channel_tools:
            if tool_config.get("toolnumber") == tool_number:
                return tool_config
        return None

    def get_required_tool_config(self, tool_number: int) -> JsonDict:
        """Retourne la configuration JSON de l'outil ou leve une erreur s'il est introuvable."""
        tool_config = self.get_tool_config(tool_number)
        if tool_config is None:
            raise ValueError(f"MachineConfigError: outil {tool_number} introuvable dans le canal {self.channel_name}")
        return tool_config

    def get_spindle_code_for_tool(self, tool_number: int, spindle_direction: SpindleDirection | None = None) -> str:
        """Retourne le code ISO de broche associe a l'outil et au sens demandes."""
        tool_config = self.get_required_tool_config(tool_number)
        if spindle_direction == SpindleDirection.CLW:
            spindle_code = tool_config.get("spindleclwstart")
        elif spindle_direction == SpindleDirection.CCLW:
            spindle_code = tool_config.get("spindlecclwstart")
        elif spindle_direction is None:
            spindle_code = tool_config.get("spindlestop")
        else:
            raise ValueError(f"MachineConfigError: sens de broche '{spindle_direction}' non supporte")

        if not spindle_code:
            raise ValueError(
                f"MachineConfigError: code de broche absent pour l'outil {tool_number} dans le canal {self.channel_name}"
            )
        return normalize_gm_code(str(spindle_code))

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
            channel_name = next(iter(machine_config["channelslist"]))
        except StopIteration:
            raise ValueError("MachineConfigError: aucun canal n'est defini dans le fichier JSON")
        return cls.from_config(machine_config, channel_name)

    @classmethod
    def from_config(machine_parameters_builder, machine_config: JsonDict, channel_name: str) -> "MachineParameters":
        """Construit les parametres machine/canal a partir du JSON charge."""
        try:
            machine_informations: JsonDict = machine_config["machineinformations"]  # type: ignore[assignment]
            channels_list: JsonDict = machine_config["channelslist"]  # type: ignore[assignment]
            channel_config: JsonDict = channels_list[channel_name]  # type: ignore[index]
            home_tool_x, home_tool_y, home_tool_z = _extract_home_tool_coordinates(channel_config["hometool"])
            # x_diameter = machine_informations["xdiameter"]
            # if x_diameter:
            #     home_tool_x = home_tool_x / 2

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
                home_tool_x=home_tool_x,
                home_tool_y=home_tool_y,
                home_tool_z=home_tool_z,
                channel_tools=channel_config["listoftools"],
                ipartvector=machine_informations.get("ipartvector"),
                jpartvector=machine_informations.get("jpartvector"),
                kpartvector=machine_informations.get("kpartvector"),
                ipathvector=channel_config.get("ipathvector"),
                jpathvector=channel_config.get("jpathvector"),
                kpathvector=channel_config.get("kpathvector"),
            )
        except KeyError:
            raise ValueError("MachineConfigError: une cle est absente dans le fichier JSON")
