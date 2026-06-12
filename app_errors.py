from __future__ import annotations


class ErrorCategory:
    """Categories d'erreurs affichees a l'utilisateur."""

    APT_INPUT = "AptInputError"
    CATIA_CONFIG = "CatiaConfigError"
    FEEDRATE = "FeedrateError"
    GEOMETRY = "GeometryError"
    MACHINE_CONFIG = "MachineConfigError"
    MACHINING_PROFILE = "MachiningProfileError"
    SYMMETRY = "SymmetryError"
    TOOLPATH_CONFIG = "ToolPathConfigError"
    TOOLPATH_DATA = "ToolPathDataError"
    TOOL_TRANSITION = "ToolTransitionError"


def error_message(category: str, detail: str) -> str:
    """Construit un message d'erreur homogene."""
    return f"{category}: {detail}"


def unmanaged_diagnostic(command: str, argument_text: str = "", reason: str | None = None) -> str:
    """Construit un diagnostic ISO pour une commande non geree."""
    command_text = f"{command}/{argument_text}".strip("/")
    if reason:
        return f"NON GERE: {command_text} ({reason})"
    return f"NON GERE: {command_text}"


def iso_error(detail: str) -> str:
    """Construit un diagnostic ISO bloquant ou potentiellement dangereux."""
    return f"ERREUR ISO: {detail}"
