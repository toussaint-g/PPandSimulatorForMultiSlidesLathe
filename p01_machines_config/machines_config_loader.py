# -*- coding: utf-8 -*-

import json
from typing import TypeAlias


JsonDict: TypeAlias = dict[str, object]


class MachinesConfigLoader:
    """Cette classe permet de gerer la configuration des machines (json)"""
    data: JsonDict = {}
    machines_list: dict[str, JsonDict] = {}

    @staticmethod
    def load_config():
        """Charge le fichier JSON et split application / machineslist"""
        try:
            with open('p02_machines_config\\machines_config.json', 'r', encoding='utf-8') as file:
                MachinesConfigLoader.data = json.load(file)

            MachinesConfigLoader.machines_list = MachinesConfigLoader.data.get('machineslist', {})  # type: ignore[assignment]

        except FileNotFoundError:
            raise FileNotFoundError(
                'Erreur : Le fichier des configurations machines (.json) est introuvable.'
            )

    @staticmethod
    def get_machines_names():
        """Retourne la liste des noms de machines (cles du JSON)"""
        return sorted(MachinesConfigLoader.machines_list.keys())

    @staticmethod
    def get_channels_list():
        """Retourne la liste des canaux pour la premiere machine disponible"""
        machine_names = MachinesConfigLoader.get_machines_names()
        if not machine_names:
            return []
        return MachinesConfigLoader.get_channels_list_for_machine(machine_names[0])

    @staticmethod
    def get_channels_list_for_machine(machine_name: str):
        """Retourne la liste des canaux d'une machine donnee"""
        machine_config: JsonDict = MachinesConfigLoader.get_machine(machine_name)
        channels: JsonDict = machine_config.get('channelslist', {})  # type: ignore[assignment]
        return sorted(channels.keys())

    @staticmethod
    def get_machine(machine_name: str) -> JsonDict:
        """Retourne le dict de la machine"""
        return MachinesConfigLoader.machines_list.get(machine_name, {})
