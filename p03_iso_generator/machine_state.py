# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from p02_machines_config.machine_enums import FeedrateUnit, MotionMode, SpindleDirection, SpindleUnit, ToolType, ToolComp


@dataclass
class WriterState:
    """L'etat logique courant de la machine tel que "vu" par le post-processeur."""

    motion_mode: MotionMode = MotionMode.RAPID
    toolComp_mode: ToolComp = ToolComp.OFF
    channel_identifier: Optional[int] = None

    feedrate_value: Optional[float] = None
    feedrate_unit: Optional[FeedrateUnit] = None
    spindle_speed: Optional[float] = None
    spindle_unit: Optional[SpindleUnit] = None
    spindle_direction: Optional[SpindleDirection] = None
    spindle_on: bool = False
    
    tool_comment: Optional[str] = None
    tool_number: Optional[int] = None
    tool_type: Optional[ToolType] = None
    previous_tool_type: Optional[ToolType] = None
    coolant_on: bool = False

    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0

    indirv_x: Optional[float] = None
    indirv_y: Optional[float] = None
    indirv_z: Optional[float] = None

    bloc_number: int = 0
    line_number: int = 0


@dataclass
class EmissionState:
    """L'etat du dernier contenu deja emis dans la sortie ISO."""

    last_x_position: Optional[float] = None
    last_y_position: Optional[float] = None
    last_z_position: Optional[float] = None

    last_feedrate_value: Optional[float] = None
    last_feedrate_unit: Optional[FeedrateUnit] = None

    last_tool_number: Optional[int] = None
    last_spindle_speed: Optional[float] = None
    last_spindle_direction: Optional[SpindleDirection] = None

    last_work_plane_code: Optional[str] = None

    last_toolComp_mode: ToolComp = ToolComp.OFF
    
