# -*- coding: utf-8 -*-

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from p01_machines_config.machine_parameters import JsonDict


def _format_value(value: Any) -> str:
    """Formate une valeur JSON pour un affichage HTML compact."""
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if value is None:
        return ""
    return str(value)


def _resource_uri(resource_name: str) -> str:
    """Retourne une URI file:// vers les ressources HTML locales."""
    resource_path = Path(__file__).resolve().parents[1] / "dev_resources" / "html" / "Ressources" / resource_name
    return resource_path.as_uri()


def _machine_image_uri(machine_config: JsonDict) -> str:
    """Retourne une URI file:// vers l'image cinematique declaree dans la config."""
    image_path = machine_config.get("imgkinematic")
    if not isinstance(image_path, str) or not image_path:
        return ""

    image_path = Path(image_path)
    if not image_path.is_absolute():
        image_path = Path(__file__).resolve().parents[1] / image_path

    return image_path.as_uri() if image_path.exists() else ""


def _safe_filename(name: str) -> str:
    """Nettoie un nom de machine pour l'utiliser comme nom de fichier."""
    safe_characters = [character if character.isalnum() or character in ("-", "_") else "_" for character in name]
    return "".join(safe_characters).strip("_") or "machine"


def _two_column_table(items: list[tuple[str, Any]]) -> str:
    rows = "\n".join(
        f"""
                    <tr>
                        <th>{escape(key)}</th>
                        <td>{escape(_format_value(value))}</td>
                    </tr>"""
        for key, value in items
    )
    return f"""
            <div class="table-wrap">
                <table>
                    <tbody>{rows}
                    </tbody>
                </table>
            </div>"""


def _matrix_table(row_label: str, rows_data: dict[str, JsonDict], extra_columns: list[tuple[str, Any]] | None = None) -> str:
    columns: list[str] = []
    for row_config in rows_data.values():
        if isinstance(row_config, dict):
            for key in row_config.keys():
                if key not in columns:
                    columns.append(key)

    extra_columns = extra_columns or []
    header_extra = "".join(f"<th>{escape(column_name)}</th>" for column_name, _value in extra_columns)
    header = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body_rows = []

    for row_name, row_config in rows_data.items():
        if not isinstance(row_config, dict):
            continue
        cells = "".join(f"<td>{escape(_format_value(value))}</td>" for _column_name, value in extra_columns)
        cells += "".join(f"<td>{escape(_format_value(row_config.get(column)))}</td>" for column in columns)
        body_rows.append(
            f"""
                    <tr>
                        <th>{escape(row_name)}</th>
                        {cells}
                    </tr>"""
        )

    return f"""
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>{escape(row_label)}</th>
                            {header_extra}
                            {header}
                        </tr>
                    </thead>
                    <tbody>{"".join(body_rows)}
                    </tbody>
                </table>
            </div>"""


def _tools_table(channels: JsonDict) -> str:
    tools_by_row: dict[str, JsonDict] = {}
    for channel_name, channel_config in channels.items():
        if not isinstance(channel_config, dict):
            continue
        tools = channel_config.get("listoftools", {})
        if not isinstance(tools, dict):
            continue
        for tool_name, tool_config in tools.items():
            if isinstance(tool_config, dict):
                tools_by_row[f"Canal {channel_name} / T{tool_name}"] = tool_config

    return _matrix_table("Outil", tools_by_row) if tools_by_row else "<p class=\"empty\">Aucun outil declare.</p>"


def build_machine_html(machine_name: str, machine_config: JsonDict) -> str:
    """Construit la fiche HTML de la machine selectionnee."""
    machine_infos = machine_config.get("machineinformations", {})
    spindles = machine_config.get("listofspindles", {})
    channels = machine_config.get("listofchannels", {})

    if not isinstance(machine_infos, dict):
        machine_infos = {}
    if not isinstance(spindles, dict):
        spindles = {}
    if not isinstance(channels, dict):
        channels = {}

    general_items = [
        (key, value)
        for key, value in machine_config.items()
        if key not in ("machineinformations", "listofspindles", "listofchannels")
    ]

    channels_summary = {
        channel_name: {
            key: value
            for key, value in channel_config.items()
            if key != "listoftools"
        }
        for channel_name, channel_config in channels.items()
        if isinstance(channel_config, dict)
    }

    logo_uri = _resource_uri("logo_sans_fond_small.png")
    kinematic_icon_uri = _resource_uri("kinematic.png")
    globals_parameters_icon_uri = _resource_uri("globals_parameters.png")
    iso_parameters_icon_uri = _resource_uri("iso_parameters.png")
    spindles_icon_uri = _resource_uri("spindles.png")
    channels_icon_uri = _resource_uri("channels.png")
    tools_icon_uri = _resource_uri("tools.png")
    information_icon_uri = _resource_uri("information.png")
    warning_icon_uri = _resource_uri("warning.png")
    machine_image_uri = _machine_image_uri(machine_config)
    machine_image_block = (
        f"""
        <div class="section-block">
            <div class="section-heading"><img src="{kinematic_icon_uri}" alt=""><h1>Cinematique machine</h1></div>
            <div class="machine-visual"><img src="{machine_image_uri}" alt="Cinematique machine {escape(machine_name)}"></div>
        </div>"""
        if machine_image_uri
        else ""
    )
    general_table = _two_column_table(general_items)
    machine_infos_table = _two_column_table(list(machine_infos.items()))
    spindles_table = _matrix_table("Broche", spindles) if spindles else '<p class="empty">Aucune broche declaree.</p>'
    channels_table = _matrix_table("Canal", channels_summary) if channels_summary else '<p class="empty">Aucun canal declare.</p>'
    tools_table = _tools_table(channels)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration machine - {escape(machine_name)}</title>
    <link rel="icon" href="{_resource_uri("LogoFondBlancICO.ico")}" type="image/x-icon">
    <style>
        :root {{
            --accent: rgb(55, 131, 138);
            --accent-dark: rgb(41, 102, 108);
            --accent-light: rgba(55, 131, 138, 0.12);
            --text: #273238;
            --muted: #5c6870;
            --page-bg: #f4f7f8;
            --white: #ffffff;
            --line: rgba(55, 131, 138, 0.22);
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background:
                linear-gradient(90deg, var(--accent) 0, var(--accent) 14px, transparent 14px),
                linear-gradient(135deg, #eef4f5 0%, #ffffff 45%, #edf5f6 100%);
            margin: 0;
            padding: 0;
            color: var(--text);
        }}

        .container {{
            background-color: transparent;
            padding: 22px 42px 40px 56px;
            margin: 0 auto;
            max-width: 1280px;
            width: 100%;
        }}

        .top-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            padding: 18px 0 24px;
            border-bottom: 4px solid var(--accent);
            margin-bottom: 26px;
            text-align: center;
        }}

        .logo {{
            width: 150px;
            max-height: 90px;
            object-fit: contain;
        }}

        .header-title {{
            flex: 1;
            margin: 0;
            color: var(--accent-dark);
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}

        .info-panel {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin: 0 0 30px;
        }}

        .news,
        .note {{
            font-size: 17px;
            margin: 0;
            padding: 16px 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 86px;
            background-color: var(--white);
            border-left: 7px solid var(--accent);
            border-radius: 0 12px 12px 0;
            box-shadow: 0 6px 18px rgba(39, 50, 56, 0.08);
            color: var(--muted);
            line-height: 1.35;
            text-align: center;
        }}

        .news {{ color: var(--accent-dark); }}
        .note {{ color: #9b3b36; }}
        .note img, .news img {{
            margin-right: 12px;
            max-height: 40px;
            max-width: 40px;
        }}

        .section-block {{
            margin: 34px 0 18px;
            padding: 22px 20px 26px;
            background-color: rgba(255, 255, 255, 0.72);
            border-left: 7px solid var(--accent);
            border-radius: 0 16px 16px 0;
        }}

        .section-heading {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 18px;
            border-bottom: 1px solid rgba(55, 131, 138, 0.25);
            padding-bottom: 10px;
        }}

        .section-heading img {{
            max-height: 58px;
            max-width: 58px;
            filter: drop-shadow(0 4px 8px rgba(39, 50, 56, 0.10));
        }}

        h1 {{
            font-size: 26px;
            color: var(--accent-dark);
            margin: 0;
        }}

        .machine-visual {{
            background-color: var(--white);
            border: 1px solid var(--line);
            border-radius: 0 12px 12px 0;
            box-shadow: 0 6px 18px rgba(39, 50, 56, 0.06);
            padding: 18px;
            text-align: center;
        }}

        .machine-visual img {{
            display: block;
            max-width: 100%;
            max-height: 500px;
            margin: 0 auto;
            object-fit: contain;
        }}

        .table-wrap {{
            width: 100%;
            overflow-x: auto;
            background-color: var(--white);
            border: 1px solid var(--line);
            border-radius: 0 12px 12px 0;
            box-shadow: 0 6px 18px rgba(39, 50, 56, 0.06);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th,
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e7eef0;
            text-align: left;
            vertical-align: top;
            white-space: nowrap;
        }}

        th {{
            color: var(--accent-dark);
            background-color: var(--accent-light);
            font-weight: 700;
        }}

        tbody tr:last-child th,
        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .empty {{
            margin: 0;
            color: var(--muted);
        }}

        .legend {{
            margin-top: 42px;
            padding: 20px;
            font-size: 18px;
            color: var(--muted);
            background-color: var(--accent-light);
            border-left: 7px solid var(--accent);
            border-radius: 0 14px 14px 0;
        }}

        .legend p {{ margin: 8px 0; }}

        @media (max-width: 760px) {{
            .container {{ padding: 16px 22px 28px 38px; }}
            .top-bar, .info-panel {{ grid-template-columns: 1fr; flex-direction: column; }}
            .header-title {{ font-size: 21px; }}
            .info-panel {{ display: block; }}
            .news, .note {{ margin-bottom: 14px; }}
            th, td {{ white-space: normal; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="top-bar">
            <img src="{logo_uri}" alt="Logo gauche" class="logo">
            <p class="header-title">Configuration machine - {escape(machine_name)}</p>
            <img src="{logo_uri}" alt="Logo droite" class="logo">
        </div>

        <div class="info-panel">
            <p class="news"><img src="{information_icon_uri}" alt="Information" width="50" height="50">Fiche generee depuis la machine selectionnee dans PPandSimulatorForMultiSlidesLathe.</p>
            <p class="note"><img src="{warning_icon_uri}" alt="Attention" width="45" height="45">Cette page est un affichage des donnees JSON machine. Les modifications restent a faire dans machines_config.json.</p>
        </div>
{machine_image_block}

        <div class="section-block">
            <div class="section-heading"><img src="{globals_parameters_icon_uri}" alt=""><h1>Informations generales</h1></div>
            {general_table}
        </div>

        <div class="section-block">
            <div class="section-heading"><img src="{iso_parameters_icon_uri}" alt=""><h1>Parametres ISO machine</h1></div>
            {machine_infos_table}
        </div>

        <div class="section-block">
            <div class="section-heading"><img src="{spindles_icon_uri}" alt=""><h1>Broches</h1></div>
            {spindles_table}
        </div>

        <div class="section-block">
            <div class="section-heading"><img src="{channels_icon_uri}" alt=""><h1>Canaux</h1></div>
            {channels_table}
        </div>

        <div class="section-block">
            <div class="section-heading"><img src="{tools_icon_uri}" alt=""><h1>Outils par canal</h1></div>
            {tools_table}
        </div>

        <div class="legend">
            <p><strong>Source :</strong> p01_machines_config/machines_config.json</p>
            <p><strong>Machine :</strong> {escape(machine_name)}</p>
        </div>
    </div>
</body>
</html>
"""


def write_machine_html(output_folder: Path, machine_name: str, machine_config: JsonDict) -> Path:
    """Ecrit la fiche HTML de la machine selectionnee et retourne son chemin."""
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / f"{_safe_filename(machine_name)}_config.html"
    output_path.write_text(build_machine_html(machine_name, machine_config), encoding="utf-8", newline="\n")
    return output_path
