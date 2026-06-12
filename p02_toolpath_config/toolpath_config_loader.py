# -*- coding: utf-8 -*-

import json
from typing import TypeAlias

from app_errors import ErrorCategory, error_message


JsonDict: TypeAlias = dict[str, object]


class ToolPathConfigLoader:
    """Cette classe permet de gerer la configuration du viewer toolpath (json)."""

    data: JsonDict = {}

    @staticmethod
    def load_config():
        """Charge le fichier JSON de configuration du viewer toolpath."""
        try:
            with open("p02_toolpath_config\\toolpath_config.json", "r", encoding="utf-8") as file:
                ToolPathConfigLoader.data = json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(
                error_message(
                    ErrorCategory.TOOLPATH_CONFIG,
                    "le fichier de configuration toolpath (.json) est introuvable",
                )
            )
