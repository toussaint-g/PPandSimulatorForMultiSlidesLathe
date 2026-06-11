# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from p01_machines_config.machine_enums import FeedrateUnit, MotionMode, RotationDirection, RotationUnit, ToolType, ToolComp


@dataclass
class WriterState:
    """L'etat logique courant de la machine tel que "vu" par le post-processeur."""
    # Feedrate
    feedrate_value: Optional[float] = None
    feedrate_unit: Optional[FeedrateUnit] = None
    # Spindle
    spindle_number: Optional[int] = None
    spindle_on: bool = False
    spindle_vector_i: Optional[float] = None
    spindle_vector_j: Optional[float] = None
    spindle_vector_k: Optional[float] = None
    # Rotation
    rotation_speed: Optional[float] = None
    rotation_unit: Optional[RotationUnit] = None
    rotation_direction: Optional[RotationDirection] = None
    # Tool
    tool_comment: Optional[str] = None
    tool_number: Optional[int] = None
    tool_type: Optional[ToolType] = None
    linked_spindle_number: Optional[int] = None
    # Coolant
    coolant_on: bool = False
    # Position
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    position_c: float = 0.0
    # Indirv
    indirv_x: Optional[float] = None
    indirv_y: Optional[float] = None
    indirv_z: Optional[float] = None
    # Other
    motion_mode: MotionMode = MotionMode.RAPID
    toolComp_mode: ToolComp = ToolComp.OFF
    channel_identifier: Optional[int] = None
    bloc_number: int = 0
    line_number: int = 0
    tool_change_processing: bool = False


@dataclass
class EmissionState:
    """L'etat du dernier contenu deja emis dans la sortie ISO et sert a eviter les emissions redondantes."""
    # Last position
    last_x_position: Optional[float] = None
    last_y_position: Optional[float] = None
    last_z_position: Optional[float] = None
    last_c_position: Optional[float] = None
    # Feedrate
    last_feedrate_value: Optional[float] = None
    last_feedrate_unit: Optional[FeedrateUnit] = None
    # Tool
    last_tool_number: Optional[int] = None
    last_tool_type:  Optional[ToolType] = None
    last_linked_spindle_number: Optional[int] = None
    # Spindle
    last_spindle_number: Optional[int] = None
    # Rotation
    last_rotation_speed: Optional[float] = None
    last_rotation_unit: Optional[RotationUnit] = None
    last_rotation_direction: Optional[RotationDirection] = None
    # Other
    last_work_plane_code: Optional[str] = None
    last_toolComp_mode: ToolComp = ToolComp.OFF
    
