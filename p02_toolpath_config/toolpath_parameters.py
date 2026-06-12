# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias

from app_errors import ErrorCategory, error_message


JsonDict: TypeAlias = dict[str, object]


@dataclass
class ToolPathParameters:
    """Regroupe les donnees utiles extraites du JSON de configuration toolpath."""

    viewer_background_color: str
    viewer_text_color: str
    viewer_text_size: int
    viewer_object_color: str
    viewer_origin_color: str
    viewer_origin_diameter: float
    viewer_compass_size: float
    tool_path_width: float
    tool_path_rapid_move_color: str
    tool_path_work_move_color: str
    tool_path_caxismove_color: str
    tool_path_cursor_point_color: str
    tool_path_cursor_point_size: int
    tool_path_circle_resolution: float
    tool_path_c_axis_resolution: float

    @classmethod
    def from_config(toolpath_parameters_builder, toolpath_config: JsonDict) -> "ToolPathParameters":
        """Construit les parametres viewer/toolpath a partir du JSON charge."""
        try:
            viewer_config: JsonDict = toolpath_config["viewer"]  # type: ignore[assignment]
            toolpath_viewer_config: JsonDict = toolpath_config["toolpath"]  # type: ignore[assignment]

            return toolpath_parameters_builder(
                viewer_background_color=viewer_config["backgroundcolor"],
                viewer_text_color=viewer_config["textinfocolor"],
                viewer_text_size=viewer_config["textinfosize"],
                viewer_object_color=viewer_config["objectcolor"],
                viewer_origin_color=viewer_config["origincolor"],
                viewer_origin_diameter=viewer_config["origindiameter"],
                viewer_compass_size=viewer_config["compasssize"],
                tool_path_width=toolpath_viewer_config["pathwidth"],
                tool_path_rapid_move_color=toolpath_viewer_config["rapidmovecolor"],
                tool_path_work_move_color=toolpath_viewer_config["workmovecolor"],
                tool_path_caxismove_color=toolpath_viewer_config["caxismovecolor"],
                tool_path_cursor_point_color=toolpath_viewer_config["cursorpointcolor"],
                tool_path_cursor_point_size=toolpath_viewer_config["cursorpointsize"],
                tool_path_circle_resolution=toolpath_viewer_config["circleresolution"],
                tool_path_c_axis_resolution=toolpath_viewer_config["caxisresolution"],
            )
        except KeyError:
            raise ValueError(error_message(
                ErrorCategory.TOOLPATH_CONFIG,
                "une cle est absente dans le fichier JSON",
            ))
