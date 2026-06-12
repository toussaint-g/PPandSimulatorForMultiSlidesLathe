
# -*- coding: utf-8 -*-

# Librairie standard
from pathlib import Path
from datetime import datetime
import tkinter
import tkinter as tk
from tkinter import filedialog, messagebox
from ttkbootstrap import Style
import ttkbootstrap as tb 
from PIL import Image, ImageTk
import os
import re

# Modules internes
from app_errors import ErrorCategory, error_message
from p04_iso_analyzer.iso_interpreter import IsoInterpreter
from p04_iso_analyzer.iso_analyzer_writer import IsoAnalyzerWriter
from p01_machines_config.machine_parameters import JsonDict
from p01_machines_config.machines_config_loader import MachinesConfigLoader
from p01_machines_config.machine_html_writer import write_machine_html
from p05_toolpath_constructor.toolpath_viewer import ToolPathViewer
from p02_toolpath_config.toolpath_config_loader import ToolPathConfigLoader
from p03_iso_generator.apt2iso import convert_file


# Fonction selection de fichier
def file_select(file_type, file_ext, label, update_calculate_button):
    """ Fonction de selection de fichier """
    file = tkinter.filedialog.askopenfilename(title="Selectionner un fichier", filetypes=[(file_type, file_ext)])
    if file:
        label.config(text=file)
        update_calculate_button()  # Met A  jour l'etat du bouton "Calculer"


# Fonction selection de dossier
def folder_select(label):
    """ Fonction de selection de dossier """
    folder = tkinter.filedialog.askdirectory(title="Selectionner un dossier")
    if folder:
        label.config(text=folder)


# Fonction pour nom de fichier A  la date et heure du jour
def get_datetime_string():
    """ Retourne la date et l'heure sous la forme YYYY-MM-DD_HH-MM-SS """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def show_operation_error(title, error):
    """Affiche une erreur utilisateur de maniere homogene dans l'interface."""
    messagebox.showerror(title, str(error))


def run_ui_action(error_title, action):
    """Execute une action UI et affiche une messagebox en cas d'erreur."""
    try:
        return action()
    except Exception as error:
        show_operation_error(error_title, error)
        return None











# Fonction traitement APT
def apt_treatment(path_apt_file, path_export_file, machine_name, channel_name):

    # Charge les config
    MachinesConfigLoader.load_config()

    # Recupere la config de la machine selectionnee
    machine_config: JsonDict = MachinesConfigLoader.get_machine(machine_name)

    # Instanciation des classes
    # obj_interpreter = AptInterpreter(machine_config, channel_name) 
    # obj_writer = AptAnalyserWriter(machine_config)

    # list_datas = obj_interpreter.analyze(path_apt_file) # Recup data
    # obj_writer.write_iso_file(Path(path_export_file).with_suffix(".nc"), path_apt_file, list_datas) # Creation du rapport

    #display_results(path_export_file)

    if not path_apt_file:
        raise ValueError(error_message(ErrorCategory.APT_INPUT, "selectionne un fichier APT source"))

    path_export_file.mkdir(parents=True, exist_ok=True)

    in_path = Path(path_apt_file)
    debug_path = path_export_file / (in_path.stem + ".debug")
    nc_path = path_export_file / (in_path.stem + ".nc")

    convert_file(str(in_path), str(debug_path), machine_config, channel_name, str(nc_path))


    # TODO: a enlever???
    os.startfile(debug_path)



    messagebox.showinfo("Conversion terminee", f"ISO genere :\n{nc_path}\n\nDebug genere :\n{debug_path}")













# Fonction traitement G-Code
def gcode_treatment(path_gcode_file, path_export_file, machine_name, channel_name):

    # Charge les config
    MachinesConfigLoader.load_config()

    # Recupere la config de la machine selectionnee
    machine_config: JsonDict = MachinesConfigLoader.get_machine(machine_name)

    # Instanciation des classes
    obj_interpreter = IsoInterpreter(machine_config, channel_name) 
    obj_writer = IsoAnalyzerWriter(machine_config)

    list_datas = obj_interpreter.analyze(path_gcode_file) # Recup data
    obj_writer.write_report(Path(path_export_file).with_suffix(".txt"), path_gcode_file, list_datas) # Creation du rapport
    obj_writer.write_debug_file(Path(path_export_file).with_suffix(".debug"), path_gcode_file, list_datas) # Creation du fichier debug

    display_results(path_export_file)


def display_results(path_export_file):
    """ Affiche la fenetre avec le resultat de l'analyse du G Code """

    result_window = tk.Toplevel()
    result_window.title("PPandSimulatorForMultiSlidesLathe: Resultat")
    result_window.state('zoomed')

    result_frame = tk.Frame(result_window)
    result_frame.pack(fill="both", expand=True, padx=10, pady=10)

    result_label = tk.Label(result_frame, text="Resultat :", font=("Segoe UI", 18, "bold"))
    result_label.pack(pady=10, anchor="w")

    # Rapport
    result_text_frame = tk.Frame(result_frame)
    result_text_frame.pack(padx=10, pady=5, fill="both", expand=True)
    result_text = tk.Text(result_text_frame, height=10, width=70, font=("Segoe UI", 12))
    result_scrollbar = tk.Scrollbar(result_text_frame, command=result_text.yview)
    result_text.config(yscrollcommand=result_scrollbar.set)
    result_text.pack(side="left", fill="both", expand=True)
    result_scrollbar.pack(side="right", fill="y")

    try:
        with open(path_export_file.with_suffix(".txt"), 'r') as file:
            result_text.insert(tk.END, file.read())
    except Exception as e:
        result_text.insert(tk.END, f"Erreur lors de la lecture du fichier : {e}")
    result_text.config(state=tk.DISABLED)

    # Debug
    separator = tk.Label(result_frame, text="Debug :", font=("Segoe UI", 18, "bold"))
    separator.pack(pady=5, anchor="w")

    debug_text_frame = tk.Frame(result_frame)
    debug_text_frame.pack(padx=10, pady=5, fill="both", expand=True)
    debug_text = tk.Text(debug_text_frame, height=10, width=70, font=("Courier", 7))
    debug_scrollbar = tk.Scrollbar(debug_text_frame, command=debug_text.yview)
    debug_text.config(yscrollcommand=debug_scrollbar.set)
    debug_text.pack(side="left", fill="both", expand=True)
    debug_scrollbar.pack(side="right", fill="y")

    try:
        with open(path_export_file.with_suffix(".debug"), 'r') as file:
            debug_text.insert(tk.END, file.read())
    except Exception as e:
        debug_text.insert(tk.END, f"Erreur lors de la lecture du fichier : {e}")
    debug_text.config(state=tk.DISABLED)


# Fonction traitement G-Code
def viewer_launch(path_gcode_file, stl_path_file, machine_name, channel_name, part_thickness):
    """ Lance la visualisation des trajectoires a partir du G-Code et du STL """
    # Charge les config
    MachinesConfigLoader.load_config()
    ToolPathConfigLoader.load_config()

    machine_config: JsonDict = MachinesConfigLoader.get_machine(machine_name)

    # Instanciation des classes
    obj_interpreter = IsoInterpreter(machine_config, channel_name) 
    obj_toolpathviewer = ToolPathViewer(machine_config, channel_name, part_thickness)

    # Recup datas g-code
    list_datas = obj_interpreter.analyze(path_gcode_file)

    # Start viewer
    obj_toolpathviewer.open_viewer(stl_path_file, list_datas)


def get_optional_path_from_label(label):
    """Retourne un Path si le label contient un chemin, sinon une chaine vide."""
    label_text = label.cget("text").strip()
    return Path(label_text) if label_text else ""


def update_channel_combo(selected_machine, channel_combo, selected_channel):
    """ Met a jour la liste des canaux disponibles en fonction de la machine selectionnee """
    machine_name = selected_machine.get()
    updated_channels = MachinesConfigLoader.get_channels_list_for_machine(machine_name)
    channel_combo["values"] = updated_channels
    selected_channel.set(updated_channels[0] if updated_channels else "")


def open_machine_image_for(machine_name):
    """ Ouvre l'image de la machine selectionnee dans le visualiseur d'images par defaut du systeme """
    machine_config: JsonDict = MachinesConfigLoader.get_machine(machine_name)
    try:
        rel = machine_config["imgkinematic"]
    except KeyError:
        raise ValueError(error_message(
            ErrorCategory.MACHINE_CONFIG,
            "une cle est absente dans le fichier JSON",
        ))

    base = Path(__file__).parent
    image_path = Path(base / rel)
    if not image_path.exists():
        raise ValueError(error_message(
            ErrorCategory.MACHINE_CONFIG,
            f"l'image specifiee est introuvable : {image_path}",
        ))
    os.startfile(image_path)


def generate_machine_html_for(machine_name, output_folder):
    """Genere et ouvre une fiche HTML pour la machine selectionnee."""
    MachinesConfigLoader.load_config()
    machine_config: JsonDict = MachinesConfigLoader.get_machine(machine_name)
    if not machine_config:
        raise ValueError(error_message(
            ErrorCategory.MACHINE_CONFIG,
            f"machine introuvable : {machine_name}",
        ))

    html_path = write_machine_html(output_folder, machine_name, machine_config)
    os.startfile(html_path)
    messagebox.showinfo("HTML machine genere", f"Fiche machine generee :\n{html_path}")


def nombre_decimal_negatif_valide(nouveau_texte):
    """ Valide que l'entree est un nombre decimal negatif ou un etat intermediaire autorise """
    if nouveau_texte in ("", "-", ".", ",", "-.", "-,"):
        return True
    return re.fullmatch(r"-?(\d+([.,]\d*)?|[.,]\d+)", nouveau_texte) is not None


def update_calculate_button(label_path, buttons):
    """ Active ou desactive une liste de boutons selon la selection ISO """
    state = "normal" if label_path.cget("text") else "disabled"
    for button in buttons:
        button.config(state=state)


# Point d'entree app
def main():
    """Point d'entree de l'application"""

    # Charge les config
    MachinesConfigLoader.load_config() 

    style = Style(theme="darkly") 

    # Creation form avec nom & dimension
    form = style.master
    form.title("PPandSimulatorForMultiSlidesLathe")
    form.state('zoomed')

    # Frame principale
    main_frame = tb.Frame(form, padding=20)
    main_frame.pack(expand=True, fill="both")

    # 3 colonnes de meme largeur
    for col in range(3):
        main_frame.grid_columnconfigure(col, weight=1, uniform="main_cols")

    # Icon de l'application
    icon_app = Image.open("img/iconform.png")
    #icon_app = icon_app.resize((32, 32))
    icon_app_tk = ImageTk.PhotoImage(icon_app) # Conversion image en format Tkinter
    form.iconphoto(True, icon_app_tk) # Appliquer l'icone au formulaire

    # Titre
    tb.Label(
        main_frame,
        text="PPandSimulatorForMultiSlidesLathe",
        font=("Segoe UI", 28, "bold"),
        bootstyle="dark",
        foreground="white"
    ).grid(column=0, row=0, columnspan=3, padx=5, pady=5)

    # Logo de l'application
    logo_app = Image.open("img/logoapp.png")
    logo_app_tk = ImageTk.PhotoImage(logo_app)
    label_logo_tk = tb.Label(main_frame, image=logo_app_tk)
    label_logo_tk.grid(column=0, row=1, columnspan=3, padx=5, pady=25)
   
    # Ligne vide
    tb.Label(main_frame, text="", font=("Segoe UI", 8)).grid(column=0, row=2, sticky="w", padx=5, pady=5)



    # Colonne 1
    # Section titre post-process
    tb.Label(main_frame, text="Zone post-process :", font=("Segoe UI", 20)).grid(column=0, row=3, sticky="w", padx=5, pady=5)
    tb.Label(main_frame, text="Pour le post-process des fichiers ATP de CATIA V5.", font=("Segoe UI", 14)).grid(column=0, row=4, sticky="w", padx=5, pady=5)
    
    # Ligne vide
    tb.Label(main_frame, text="", font=("Segoe UI", 8)).grid(column=0, row=5, sticky="w", padx=5, pady=5)

    # Section APT
    tb.Label(main_frame, text="Fichier APT :", font=("Segoe UI", 16)).grid(column=0, row=6, sticky="w", padx=5, pady=5)
    label_apt_for_pp = tb.Label(main_frame, text="", width=50, bootstyle="secondary")
    label_apt_for_pp.grid(column=0, row=7, sticky="w")
    tb.Button(main_frame, text="Selectionner", bootstyle="primary", 
              command=lambda: file_select("Fichier APT", "*.aptsource", label_apt_for_pp, 
                                          lambda: update_calculate_button(label_apt_for_pp, [calculate_button_for_pp]))).grid(column=0, row=8, sticky="w", padx=5, pady=5)

    # Section dossier de sortie
    tb.Label(main_frame, text="Dossier de sortie :", font=("Segoe UI", 16)).grid(column=0, row=9, sticky="w", padx=5, pady=5)
    label_output_folder_for_pp = tb.Label(main_frame, text="C:\\Temp", width=50, bootstyle="secondary")
    label_output_folder_for_pp.grid(column=0, row=10, sticky="w")
    tb.Button(main_frame, text="Selectionner", bootstyle="primary", 
              command=lambda: folder_select(label_output_folder_for_pp)).grid(column=0, row=11, sticky="w", padx=5, pady=5)

    # Ligne vide
    tb.Label(main_frame, text="", font=("Segoe UI", 8)).grid(column=0, row=12, sticky="w", padx=5, pady=5)

    # Section machine
    tb.Label(main_frame, text="Machine cible :", font=("Segoe UI", 16)).grid(column=0, row=13, sticky="w", padx=5, pady=5)
    # Donnees fournies par le JSON
    machines_list_for_pp = MachinesConfigLoader.get_machines_names()
    selected_machine_for_pp = tk.StringVar(value=machines_list_for_pp[0] if machines_list_for_pp else "")
    machine_combo_for_pp = tb.Combobox(
        main_frame,
        textvariable=selected_machine_for_pp,
        values=machines_list_for_pp,
        state="readonly",
        width=47,
        bootstyle="secondary"
    )
    machine_combo_for_pp.grid(column=0, row=14, sticky="w", padx=5, pady=5)

    # Section canal machine
    tb.Label(main_frame, text="Canal de la machine :", font=("Segoe UI", 16)).grid(column=0, row=15, sticky="w", padx=5, pady=5)
    # Donnees fournies par le JSON
    channels_list_for_pp = MachinesConfigLoader.get_channels_list_for_machine(selected_machine_for_pp.get())
    selected_channel_for_pp = tk.StringVar(value=channels_list_for_pp[0] if channels_list_for_pp else "")
    channel_combo_for_pp = tb.Combobox(
        main_frame,
        textvariable=selected_channel_for_pp,
        values=channels_list_for_pp,
        state="readonly",
        width=47,
        bootstyle="secondary"
    )
    channel_combo_for_pp.grid(column=0, row=16, sticky="w", padx=5, pady=5)

    machine_combo_for_pp.bind(
        "<<ComboboxSelected>>",
        lambda _event: update_channel_combo(selected_machine_for_pp, channel_combo_for_pp, selected_channel_for_pp),
    )

    # Ligne vide
    tb.Label(main_frame, text="", font=("Segoe UI", 8)).grid(column=0, row=17, sticky="w", padx=5, pady=5)

    # Section generer le fichier ISO
    tb.Label(main_frame, text="Generer le fichier ISO :", font=("Segoe UI", 16)).grid(column=0, row=18, sticky="w", padx=5, pady=5)

    # Section calculer les donnees
    calculate_button_for_pp = tb.Button(main_frame, text="Start", bootstyle="success", command=lambda: run_ui_action(
        "Erreur conversion",
        lambda: apt_treatment(
            Path(label_apt_for_pp.cget("text")),
            Path(label_output_folder_for_pp.cget("text")) / get_datetime_string(),
            selected_machine_for_pp.get(),
            selected_channel_for_pp.get(),
        ),
    ))
    calculate_button_for_pp.grid(column=0, row=19, sticky="w", pady=5)
    calculate_button_for_pp.config(state="disabled")  # Desactiver au debut



    # Colonne 2
    # Section titre analyse
    tb.Label(main_frame, text="Zone analyse :", font=("Segoe UI", 20)).grid(column=1, row=3, sticky="w", padx=5, pady=5)
    tb.Label(main_frame, text="Pour l'analyse des temps d'usinage des fichiers ISO.", font=("Segoe UI", 14)).grid(column=1, row=4, sticky="w", padx=5, pady=5)

    # Section code ISO
    tb.Label(main_frame, text="Fichier ISO :", font=("Segoe UI", 16)).grid(column=1, row=6, sticky="w", padx=5, pady=5)
    label_iso_file_for_analyzer = tb.Label(main_frame, text="", width=50, bootstyle="secondary")
    label_iso_file_for_analyzer.grid(column=1, row=7, sticky="w")
    tb.Button(main_frame, text="Selectionner", bootstyle="primary", 
              command=lambda: file_select("Fichier ISO", "*.anc;*.nc;*.txt;*.path1;*.path2;*.path3", label_iso_file_for_analyzer, 
                                          lambda: update_calculate_button(label_iso_file_for_analyzer, [calculate_button_for_analyzer, visualize_button_for_analyzer]))).grid(column=1, row=8, sticky="w", padx=5, pady=5)

    # Section dossier de sortie
    tb.Label(main_frame, text="Dossier de sortie :", font=("Segoe UI", 16)).grid(column=1, row=9, sticky="w", padx=5, pady=5)
    label_output_folder_for_analyzer = tb.Label(main_frame, text="C:\\Temp", width=50, bootstyle="secondary")
    label_output_folder_for_analyzer.grid(column=1, row=10, sticky="w")
    tb.Button(main_frame, text="Selectionner", bootstyle="primary", 
              command=lambda: folder_select(label_output_folder_for_analyzer)).grid(column=1, row=11, sticky="w", padx=5, pady=5)

    # Section machine
    tb.Label(main_frame, text="Machine cible :", font=("Segoe UI", 16)).grid(column=1, row=13, sticky="w", padx=5, pady=5)
    # Donnees fournies par le JSON
    machines_list_for_analyzer = MachinesConfigLoader.get_machines_names()
    selected_machine_for_analyzer = tk.StringVar(value=machines_list_for_analyzer[0] if machines_list_for_analyzer else "")
    machine_combo_for_analyzer = tb.Combobox(
        main_frame,
        textvariable=selected_machine_for_analyzer,
        values=machines_list_for_analyzer,
        state="readonly",
        width=47,
        bootstyle="secondary"
    )
    machine_combo_for_analyzer.grid(column=1, row=14, sticky="w", padx=5, pady=5)

    # Section canal machine
    tb.Label(main_frame, text="Canal de la machine :", font=("Segoe UI", 16)).grid(column=1, row=15, sticky="w", padx=5, pady=5)
    # Donnees fournies par le JSON
    channels_list_for_analyzer = MachinesConfigLoader.get_channels_list_for_machine(selected_machine_for_analyzer.get())
    selected_channel_for_analyzer = tk.StringVar(value=channels_list_for_analyzer[0] if channels_list_for_analyzer else "")
    channel_combo_for_analyzer = tb.Combobox(
        main_frame,
        textvariable=selected_channel_for_analyzer,
        values=channels_list_for_analyzer,
        state="readonly",
        width=47,
        bootstyle="secondary"
    )
    channel_combo_for_analyzer.grid(column=1, row=16, sticky="w", padx=5, pady=5)

    machine_combo_for_analyzer.bind(
        "<<ComboboxSelected>>",
        lambda _event: update_channel_combo(selected_machine_for_analyzer, channel_combo_for_analyzer, selected_channel_for_analyzer),
    )

    # Section calculer les donnees
    tb.Label(main_frame, text="Analyser le fichier ISO :", font=("Segoe UI", 16)).grid(column=1, row=18, sticky="w", padx=5, pady=5)    
    calculate_button_for_analyzer = tb.Button(main_frame, text="Start", bootstyle="success", command=lambda: run_ui_action(
        "Erreur analyse ISO",
        lambda: gcode_treatment(
            Path(label_iso_file_for_analyzer.cget("text")),
            Path(label_output_folder_for_analyzer.cget("text")) / get_datetime_string(),
            selected_machine_for_analyzer.get(),
            selected_channel_for_analyzer.get(),
        ),
    ))
    calculate_button_for_analyzer.grid(column=1, row=19, sticky="w", pady=5)
    calculate_button_for_analyzer.config(state="disabled")  # Desactiver au debut



    # Colonne 3
    # Section titre simulateur
    tb.Label(main_frame, text="Zone simulation :", font=("Segoe UI", 20)).grid(column=2, row=3, sticky="w", padx=5, pady=5)
    tb.Label(main_frame, text="Pour la simulation des trajectoires des fichiers ISO.\n-> Selection du fichier a simuler dans la zone ""analyse""", font=("Segoe UI", 14)).grid(column=2, row=4, sticky="w", padx=5, pady=5)

    # Section STL
    tb.Label(main_frame, text="Fichier STL :", font=("Segoe UI", 16)).grid(column=2, row=6, sticky="w", padx=5, pady=5)
    label_stl = tb.Label(main_frame, text="", width=50, bootstyle="secondary")
    label_stl.grid(column=2, row=7, sticky="w", padx=5)
    tb.Button(main_frame, text="Selectionner", bootstyle="primary", 
              command=lambda: file_select("Fichier STL", "*.stl", label_stl, 
                                          lambda: update_calculate_button(label_iso_file_for_analyzer, [calculate_button_for_analyzer, visualize_button_for_analyzer]))).grid(column=2, row=8, sticky="w", padx=5, pady=5)

    # Section visualisation de la config machine
    tb.Label(main_frame, text="Visualiser la config machine :", 
             font=("Segoe UI", 16)).grid(column=2, row=13, sticky="w", padx=5, pady=5)

    visualize_button_for_analyzer = tb.Button(main_frame, text="Visualiser", bootstyle="primary", 
                                 command=lambda: run_ui_action(
                                     "Erreur image machine",
                                     lambda: open_machine_image_for(selected_machine_for_analyzer.get()),
                                 ))
    visualize_button_for_analyzer.grid(column=2, row=14, sticky="w", padx=5, pady=5)

    generate_machine_html_button = tb.Button(main_frame, text="Generer HTML", bootstyle="primary",
                                 command=lambda: run_ui_action(
                                     "Erreur generation HTML machine",
                                     lambda: generate_machine_html_for(
                                         selected_machine_for_analyzer.get(),
                                         Path(label_output_folder_for_analyzer.cget("text")) / get_datetime_string(),
                                     ),
                                 ))
    generate_machine_html_button.grid(column=2, row=15, sticky="w", padx=5, pady=5)

    # Section decalage piece
    tb.Label(main_frame, text="Epaisseur piece (pour dec COP) :", 
             font=("Segoe UI", 16)).grid(column=2, row=16, sticky="w", padx=5, pady=5)
    
    # Validation de l'entree pour n'autoriser que les nombres decimaux negatifs et les etats intermediaires
    vcmd = (form.register(nombre_decimal_negatif_valide), "%P")
    part_thickness_var = tk.DoubleVar(value=0.0)
    part_thickness = tb.Entry(
        main_frame,
        textvariable=part_thickness_var,
        width=50,
        bootstyle="secondary",
        validate="key",
        validatecommand=vcmd
    )
    part_thickness.grid(column=2, row=17, sticky="w", padx=5, pady=5)

    # Section Visualiser les trajectoires
    tb.Label(main_frame, text="Visualiser les trajectoires :", font=("Segoe UI", 16)).grid(column=2, row=19, sticky="w", padx=5, pady=5)
    visualize_button_for_analyzer = tb.Button(main_frame, text="Start", bootstyle="success", command=lambda: run_ui_action(
        "Erreur simulation",
        lambda: viewer_launch(
            Path(label_iso_file_for_analyzer.cget("text")), 
            get_optional_path_from_label(label_stl),
            selected_machine_for_analyzer.get(), 
            selected_channel_for_analyzer.get(),
            part_thickness_var.get(),
        ),
    ))
    visualize_button_for_analyzer.grid(column=2, row=20, sticky="w", padx=5, pady=5)
    visualize_button_for_analyzer.config(state="disabled")  # Desactiver au debut

    update_calculate_button(
        label_path=label_iso_file_for_analyzer,
        buttons=[calculate_button_for_analyzer, visualize_button_for_analyzer],
    )

    form.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        show_operation_error("Erreur demarrage", error)
        root.destroy()
