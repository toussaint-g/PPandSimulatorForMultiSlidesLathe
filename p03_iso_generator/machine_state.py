# -*- coding: utf-8 -*-

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
from app_errors import ErrorCategory, error_message
from p01_machines_config.machine_enums import FeedrateUnit, MotionMode, RotationDirection, RotationUnit, ToolType, ToolComp

if TYPE_CHECKING:
    from p01_machines_config.machine_parameters import MachineParameters


@dataclass
class ToolSelection:
    """Selection outil courante issue des commandes APT LOADTL/TPRINT."""
    comment: Optional[str] = None
    number: Optional[int] = None
    tool_type: Optional[ToolType] = None
    linked_spindle_number: Optional[int] = None

    def copy(self) -> ToolSelection:
        """Retourne un instantane independant de la selection outil."""
        return replace(self)

    @classmethod
    def from_writer_state(cls, state: WriterState) -> ToolSelection:
        """Construit une selection outil depuis l'etat APT courant."""
        # WriterState porte deja TPRINT et LOADTL dans un seul objet.
        return state.tool.copy()


@dataclass
class SpindleSelection:
    """Selection broche courante issue des commandes APT SPINDL_NAME/SPINDL."""
    number: Optional[int] = None
    vector_i: Optional[float] = None
    vector_j: Optional[float] = None
    vector_k: Optional[float] = None
    rotation_speed: Optional[float] = None
    rotation_unit: Optional[RotationUnit] = None
    rotation_direction: Optional[RotationDirection] = None

    def copy(self) -> SpindleSelection:
        """Retourne un instantane independant de la selection broche."""
        return replace(self)

    @classmethod
    def from_writer_state(cls, state: WriterState) -> SpindleSelection:
        """Construit une selection broche depuis l'etat APT courant."""
        # WriterState porte deja SPINDL_NAME et SPINDL dans un seul objet.
        return state.spindle.copy()


@dataclass
class MachiningSelection:
    """Etat outil/broche complet a valider avant emission d'un mouvement."""
    tool: ToolSelection
    spindle: SpindleSelection

    def copy(self) -> MachiningSelection:
        """Retourne un instantane independant outil/broche."""
        return MachiningSelection(
            tool=self.tool.copy(),
            spindle=self.spindle.copy(),
        )

    @classmethod
    def from_writer_state(cls, state: WriterState) -> MachiningSelection:
        """Construit la selection complete depuis l'etat APT courant."""
        # Etat complet attendu par la validation et les transitions.
        return cls(
            tool=ToolSelection.from_writer_state(state),
            spindle=SpindleSelection.from_writer_state(state),
        )


class TransitionKind(Enum):
    """Type de passage entre le dernier etat ISO emis et l'etat courant."""
    FIRST_TURN = auto()
    FIRST_MILL = auto()
    MILL_TO_TURN = auto()
    TURN_TO_MILL = auto()
    TURN_TO_TURN = auto()
    MILL_TO_MILL = auto()
    SAME_TOOL = auto()


@dataclass
class ToolTransition:
    """Comparaison entre l'etat outil/broche deja emis et l'etat courant."""
    previous_tool: Optional[ToolSelection]
    previous_spindle: Optional[SpindleSelection]
    current_tool: ToolSelection
    current_spindle: SpindleSelection
    tool_change_processing: bool

    @classmethod
    def from_emission_state(
        cls,
        emission_state: EmissionState,
        current_tool: ToolSelection,
        current_spindle: SpindleSelection,
        tool_change_processing: bool,
    ) -> ToolTransition:
        """Construit une transition depuis le dernier etat ISO emis."""
        # last_selection remplace les anciens champs last_tool/last_spindle separes.
        previous_tool = None
        previous_spindle = None
        if emission_state.last_selection is not None:
            previous_tool = emission_state.last_selection.tool
            previous_spindle = emission_state.last_selection.spindle

        return cls(
            previous_tool=previous_tool,
            previous_spindle=previous_spindle,
            current_tool=current_tool,
            current_spindle=current_spindle,
            tool_change_processing=tool_change_processing,
        )

    @property
    def previous_tool_type(self) -> Optional[ToolType]:
        """Type du dernier outil emis."""
        return self.previous_tool.tool_type if self.previous_tool else None

    @property
    def current_tool_type(self) -> Optional[ToolType]:
        """Type de l'outil courant."""
        return self.current_tool.tool_type

    @property
    def is_first_tool(self) -> bool:
        """Vrai si aucun outil n'a encore ete emis."""
        return self.previous_tool_type is None

    @property
    def is_tool_number_change(self) -> bool:
        """Vrai si le numero outil change entre l'etat emis et l'etat courant."""
        return (
            self.previous_tool is None
            or self.previous_tool.number != self.current_tool.number
        )

    @property
    def is_spindle_change(self) -> bool:
        """Vrai si la broche declaree change."""
        return (
            self.previous_spindle is not None
            and self.previous_spindle.number != self.current_spindle.number
        )

    @property
    def is_rotation_change(self) -> bool:
        """Vrai si vitesse, unite ou direction de rotation changent."""
        if self.previous_spindle is None:
            return False
        return (
            self.previous_spindle.rotation_speed != self.current_spindle.rotation_speed
            or self.previous_spindle.rotation_unit != self.current_spindle.rotation_unit
            or self.previous_spindle.rotation_direction != self.current_spindle.rotation_direction
        )

    def validate(self) -> None:
        """Valide les regles de transition independantes du profil courant."""
        # La logique actuelle impose un LOADTL avant un changement de broche.
        if not self.tool_change_processing and self.is_spindle_change:
            raise ValueError(
                error_message(
                    ErrorCategory.CATIA_CONFIG,
                    f"changement de broche impossible sans changement d'outil prealable : {self.current_spindle.number}",
                )
            )

    def kind(self) -> TransitionKind:
        """Retourne le type de transition outil/broche."""
        previous_type = self.previous_tool_type
        current_type = self.current_tool_type

        # Sans LOADTL, on reste sur le meme outil et on traite surtout la rotation.
        if not self.tool_change_processing:
            return TransitionKind.SAME_TOOL

        # Avec LOADTL, on classe le passage pour choisir les codes ISO a emettre.
        if previous_type is None and current_type == ToolType.TURN:
            return TransitionKind.FIRST_TURN
        if previous_type is None and current_type == ToolType.MILL:
            return TransitionKind.FIRST_MILL
        if previous_type == ToolType.MILL and current_type == ToolType.TURN:
            return TransitionKind.MILL_TO_TURN
        if previous_type == ToolType.TURN and current_type == ToolType.MILL:
            return TransitionKind.TURN_TO_MILL
        if previous_type == ToolType.TURN and current_type == ToolType.TURN:
            return TransitionKind.TURN_TO_TURN
        if previous_type == ToolType.MILL and current_type == ToolType.MILL:
            return TransitionKind.MILL_TO_MILL
        raise ValueError(error_message(
            ErrorCategory.TOOL_TRANSITION,
            f"transition non supportee {previous_type} -> {current_type}",
        ))


class MachiningProfile(ABC):
    """Profil de validation des etats outil/broche avant mouvements ISO."""
    tool_type: ToolType
    profile_name: str

    def validate(self, selection: MachiningSelection, machine: MachineParameters) -> None:
        """Valide les regles communes puis les regles propres au profil."""
        # Les regles communes garantissent que l'etat est complet.
        self._validate_common(selection, machine)
        # Les regles specifiques portent les contraintes MILL/TURN.
        self._validate_specific(selection, machine)

    def _validate_common(self, selection: MachiningSelection, machine: MachineParameters) -> None:
        """Valide les informations obligatoires pour tous les profils."""
        tool = selection.tool
        spindle = selection.spindle

        if tool.number is None:
            raise ValueError(error_message(f"{self.profile_name}ProfileError", "LOADTL absent avant mouvement"))
        if tool.tool_type is None:
            raise ValueError(error_message(f"{self.profile_name}ProfileError", "type outil absent avant mouvement"))
        if tool.tool_type != self.tool_type:
            raise ValueError(
                error_message(
                    f"{self.profile_name}ProfileError",
                    f"outil {tool.number} declare {tool.tool_type.value}, profil attendu {self.tool_type.value}",
                )
            )

        json_tool_type = machine.get_tool_type(tool.number)
        if json_tool_type != tool.tool_type:
            raise ValueError(
                error_message(
                    f"{self.profile_name}ProfileError",
                    f"type outil LOADTL {tool.tool_type.value} different du JSON {json_tool_type.value} pour l'outil {tool.number}",
                )
            )

        if spindle.number is None:
            raise ValueError(error_message(f"{self.profile_name}ProfileError", "SPINDL_NAME absent avant mouvement"))
        if tool.linked_spindle_number != spindle.number:
            raise ValueError(
                error_message(
                    f"{self.profile_name}ProfileError",
                    f"broche {spindle.number} selectionnee alors que l'outil {tool.number} est lie a la broche {tool.linked_spindle_number}",
                )
            )
        if spindle.rotation_speed is None:
            raise ValueError(error_message(f"{self.profile_name}ProfileError", "vitesse SPINDL absente avant mouvement"))
        if spindle.rotation_unit is None:
            raise ValueError(error_message(f"{self.profile_name}ProfileError", "unite SPINDL absente avant mouvement"))
        if spindle.rotation_direction is None:
            raise ValueError(error_message(f"{self.profile_name}ProfileError", "direction SPINDL absente avant mouvement"))

    @abstractmethod
    def _validate_specific(self, selection: MachiningSelection, machine: MachineParameters) -> None:
        """Valide les regles propres au mode d'usinage."""


class MillProfile(MachiningProfile):
    """Profil de validation pour les outils tournants de fraisage."""
    tool_type = ToolType.MILL
    profile_name = "MILL"

    def _validate_specific(self, selection: MachiningSelection, machine: MachineParameters) -> None:
        spindle = selection.spindle

        if spindle.vector_i is None or spindle.vector_j is None or spindle.vector_k is None:
            raise ValueError(error_message("MILLProfileError", "vecteur SPINDL_NAME absent avant mouvement de fraisage"))

        tool_config = machine.get_required_tool_config(selection.tool.number)
        tool_vector = tool_config.get("ktoolvector")
        if not isinstance(tool_vector, (list, tuple)) or len(tool_vector) != 3:
            raise ValueError(
                error_message(
                    "MILLProfileError",
                    f"ktoolvector absent ou invalide pour l'outil {selection.tool.number}",
                )
            )


class TurnProfile(MachiningProfile):
    """Profil de validation pour les outils fixes de tournage."""
    tool_type = ToolType.TURN
    profile_name = "TURN"

    def _validate_specific(self, selection: MachiningSelection, machine: MachineParameters) -> None:
        return None


def get_machining_profile(tool_type: ToolType) -> MachiningProfile:
    """Retourne le profil de validation correspondant au type d'outil."""
    if tool_type == ToolType.MILL:
        return MillProfile()
    if tool_type == ToolType.TURN:
        return TurnProfile()
    raise ValueError(error_message(ErrorCategory.MACHINING_PROFILE, f"type outil non supporte {tool_type}"))


@dataclass
class WriterState:
    """L'etat logique courant de la machine tel que "vu" par le post-processeur."""
    # Feedrate
    feedrate_value: Optional[float] = None
    feedrate_unit: Optional[FeedrateUnit] = None
    # Spindle
    spindle: SpindleSelection = field(default_factory=SpindleSelection)
    # Tool
    tool: ToolSelection = field(default_factory=ToolSelection)
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
    # Tool / Spindle
    last_selection: Optional[MachiningSelection] = None
    # Other
    last_work_plane_code: Optional[str] = None
    last_toolComp_mode: ToolComp = ToolComp.OFF
    
