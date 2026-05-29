# -*- coding: utf-8 -*-

from enum import Enum


class FeedrateUnit(str, Enum):
    """Enum pour memoriser les unites d'avance autorisees."""
    MMPR = "MMPR"
    MMPM = "MMPM"


class MotionMode(str, Enum):
    """Enum pour memoriser les modes de mouvement autorises."""
    RAPID = "RAPID"
    WORKING = "WORKING"


class RotationUnit(str, Enum):
    """Enum pour memoriser les unites de rotation autorisees."""
    RPM = "RPM"
    SMM = "SMM"


class RotationDirection(str, Enum):
    """Enum pour memoriser les sens de rotation autorises."""
    CLW = "CLW"
    CCLW = "CCLW"


class ToolType(str, Enum):
    """Enum pour memoriser les types d'outil autorises."""
    TURN = "TURN"
    MILL = "MILL"


class ToolComp(str, Enum):
    """Enum pour memoriser les types de compensation d'outil autorises."""
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    OFF = "OFF"
