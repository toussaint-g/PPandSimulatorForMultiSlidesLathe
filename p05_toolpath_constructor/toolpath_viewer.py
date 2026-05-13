
# -*- coding: utf-8 -*-

# Librairie standard
#from operator import index
from pathlib import Path
import vtk
from vtkmodules.vtkCommonColor import vtkNamedColors

# Modules internes
from p01_machines_config.machine_parameters import JsonDict
from p02_toolpath_config.toolpath_config_loader import ToolPathConfigLoader
from p02_toolpath_config.toolpath_parameters import ToolPathParameters
from p05_toolpath_constructor.toolpath_interpeter import ToolPathInterpreter


class ToolPathViewer:
    """Cette classe permet la lecture et la creation d'un viewer de ficher 3D"""

    def __init__(self, machine_config: JsonDict, channel_name: str, part_thickness):
        self.machine_config = machine_config
        self.channel_name = channel_name
        self.part_thickness = part_thickness
        self.toolpath_parameters = ToolPathParameters.from_config(ToolPathConfigLoader.data)


    def open_viewer(self, path_file, list_datas):
        """Cette methode ouvre et parametre le viewer 3D"""

        # Couleurs
        colors = vtkNamedColors()
        # Acteur pour stl
        actor_stl = vtk.vtkActor()

        stl_file_path = Path(path_file) if path_file not in ("", None) else None

        # Controle de selection de fichier STL
        if stl_file_path is not None and stl_file_path.is_file():
            # Lire le fichier STL
            reader = vtk.vtkSTLReader()
            reader.SetFileName(str(stl_file_path))
            # Acteur pour stl
            mapper_stl = vtk.vtkPolyDataMapper()
            mapper_stl.SetInputConnection(reader.GetOutputPort())
            actor_stl.SetMapper(mapper_stl)
            actor_stl.GetProperty().SetColor(colors.GetColor3d(self.toolpath_parameters.viewer_object_color))
            actor_stl.GetProperty().SetAmbient(0.2)
            actor_stl.GetProperty().SetDiffuse(0.7)
            actor_stl.GetProperty().SetSpecular(0.4)
            actor_stl.GetProperty().SetSpecularPower(30)
            actor_stl.GetProperty().SetOpacity(1)

        # Acteur pour sphere d'origine
        radius = self.toolpath_parameters.viewer_origin_diameter / 2
        sphere_origine = vtk.vtkSphereSource()
        sphere_origine.SetCenter(0.0, 0.0, 0.0)
        sphere_origine.SetRadius(radius)
        sphere_origine.SetPhiResolution(30)
        sphere_origine.SetThetaResolution(30)
        sphere_origine.Update()
        mapper_origine = vtk.vtkPolyDataMapper()
        mapper_origine.SetInputConnection(sphere_origine.GetOutputPort())
        actor_origine = vtk.vtkActor()
        actor_origine.SetMapper(mapper_origine)
        actor_origine.GetProperty().SetColor(colors.GetColor3d(self.toolpath_parameters.viewer_origin_color))
        actor_origine.GetProperty().SetSpecular(0.3) # Lumiere speculaire (point de brillance)
        actor_origine.GetProperty().SetSpecularPower(20) # Nettete de cette lumiere speculaire

        point_cursor = vtk.vtkPoints()
        point_cursor.InsertNextPoint(0.0, 0.0, 0.0)
        point_cursor_vertices = vtk.vtkCellArray()
        point_cursor_vertices.InsertNextCell(1)
        point_cursor_vertices.InsertCellPoint(0)
        point_cursor_polydata = vtk.vtkPolyData()
        point_cursor_polydata.SetPoints(point_cursor)
        point_cursor_polydata.SetVerts(point_cursor_vertices)
        mapper_cursor = vtk.vtkPolyDataMapper()
        mapper_cursor.SetInputData(point_cursor_polydata)
        actor_cursor = vtk.vtkActor()
        actor_cursor.SetMapper(mapper_cursor)
        actor_cursor.GetProperty().SetColor(colors.GetColor3d(self.toolpath_parameters.tool_path_cursor_point_color))
        actor_cursor.GetProperty().SetPointSize(self.toolpath_parameters.tool_path_cursor_point_size)
        actor_cursor.SetVisibility(False)

        # Moteurs de rendu piece
        renderer_pc = vtk.vtkRenderer()
        renderer_pc.SetBackground(colors.GetColor3d(self.toolpath_parameters.viewer_background_color))
        renderer_pc.AddActor(actor_stl)
        renderer_pc.AddActor(actor_origine)
        renderer_pc.SetLayer(0)


        # Creation message texte
        text_rendu = "Escape -> masquage/affichage trajectoires\nSpace -> masquage/affichage piece\nRight/left -> defilement trajectoires\nUp/down -> defilement points\n\nRendu toolpath: "
        text = vtk.vtkTextActor()
        text.SetInput(text_rendu + "toutes trajectoires affichees")
        textprop = text.GetTextProperty()
        textprop.SetFontSize(self.toolpath_parameters.viewer_text_size)
        textprop.SetColor(colors.GetColor3d(self.toolpath_parameters.viewer_text_color))
        text.SetPosition(10, 10)
        renderer_pc.AddActor2D(text)

        # Moteurs de rendu toolpath
        renderer_toolpath = vtk.vtkRenderer()
        
        # Recup actors
        obj_tool_path_interpeter = ToolPathInterpreter(self.machine_config, self.channel_name, self.part_thickness)
        actors_list = obj_tool_path_interpeter.analyze(
            list_datas,
            self.toolpath_parameters.tool_path_circle_resolution)

        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)
        lookup_table.Build()
        rapid_color = colors.GetColor3ub(self.toolpath_parameters.tool_path_rapid_move_color)
        work_color = colors.GetColor3ub(self.toolpath_parameters.tool_path_work_move_color)
        lookup_table.SetTableValue(0, rapid_color.GetRed() / 255.0, rapid_color.GetGreen() / 255.0, rapid_color.GetBlue() / 255.0, 1.0)
        lookup_table.SetTableValue(1, work_color.GetRed() / 255.0, work_color.GetGreen() / 255.0, work_color.GetBlue() / 255.0, 1.0)

        # Boucle recup actor et ajout dans moteur rendu
        for actor_toolpath in actors_list:
            mapper_toolpath = actor_toolpath.GetMapper()
            mapper_toolpath.SetLookupTable(lookup_table)
            mapper_toolpath.SetScalarRange(0, 1)
            mapper_toolpath.ScalarVisibilityOn()
            actor_toolpath.GetProperty().SetLineWidth(self.toolpath_parameters.tool_path_width)
            renderer_toolpath.AddActor(actor_toolpath)

        renderer_toolpath.AddActor(actor_cursor)

        toolpath_points = []
        toolpath_c_values = []
        toolpath_original_points = []
        for actor_toolpath in actors_list:
            current_tool_points = []
            current_tool_c_values = []
            current_tool_original_points = []
            polydata = actor_toolpath.GetMapper().GetInput()
            vtk_points = polydata.GetPoints() if polydata is not None else None
            c_array = polydata.GetPointData().GetArray("C_angle_deg") if polydata is not None else None
            original_x_array = polydata.GetPointData().GetArray("OriginalX") if polydata is not None else None
            original_y_array = polydata.GetPointData().GetArray("OriginalY") if polydata is not None else None
            original_z_array = polydata.GetPointData().GetArray("OriginalZ") if polydata is not None else None
            if vtk_points is not None:
                for point_index in range(vtk_points.GetNumberOfPoints()):
                    current_tool_points.append(vtk_points.GetPoint(point_index))
                    current_tool_c_values.append(c_array.GetValue(point_index) if c_array is not None else 0.0)
                    current_tool_original_points.append((
                        original_x_array.GetValue(point_index) if original_x_array is not None else 0.0,
                        original_y_array.GetValue(point_index) if original_y_array is not None else 0.0,
                        original_z_array.GetValue(point_index) if original_z_array is not None else 0.0,
                    ))
            toolpath_points.append(current_tool_points)
            toolpath_c_values.append(current_tool_c_values)
            toolpath_original_points.append(current_tool_original_points)

        # Layer par dessus la piece
        renderer_toolpath.SetLayer(1)
        renderer_toolpath.SetBackgroundAlpha(0) # Transparence

        # Param form d'affichage
        render_window = vtk.vtkRenderWindow()
        render_window.AddRenderer(renderer_pc)
        render_window.AddRenderer(renderer_toolpath)
        render_window.SetNumberOfLayers(2)
        render_window.SetWindowName("Part Program Analyzer: Viewer 3D")
        render_window.SetSize(800, 800)
        screen_size = render_window.GetScreenSize()
        window_size = render_window.GetSize()
        x_pos = (screen_size[0] - window_size[0]) // 2
        y_pos = (screen_size[1] - window_size[1]) // 2
        render_window.SetPosition(x_pos, y_pos)
        
        # Cameras synchronisees
        renderer_toolpath.SetActiveCamera(renderer_pc.GetActiveCamera())

        # Variables etat
        etat_visu = {
            "current_index": -1,
            "current_point_index": 0,
            "all_visible": True
            }

        def update_toolpath_text():
            current_actor_index = etat_visu["current_index"]
            if current_actor_index < 0 or current_actor_index >= len(actors_list):
                return

            points_count = len(toolpath_points[current_actor_index])
            if points_count == 0:
                text.SetInput(f"{text_rendu} T{actors_list[current_actor_index].tag}")
                return

            current_point = etat_visu["current_point_index"] + 1
            point_x, point_y, point_z = toolpath_original_points[current_actor_index][etat_visu["current_point_index"]]
            point_c = toolpath_c_values[current_actor_index][etat_visu["current_point_index"]]
            text.SetInput(
                f"{text_rendu} T{actors_list[current_actor_index].tag} point {current_point}/{points_count}\n"
                f"X {point_x:.3f}  Y {point_y:.3f}  Z {point_z:.3f}  C {point_c:.3f}"
            )

        def update_cursor_actor():
            current_actor_index = etat_visu["current_index"]
            if current_actor_index < 0 or current_actor_index >= len(toolpath_points):
                actor_cursor.SetVisibility(False)
                return

            current_points = toolpath_points[current_actor_index]
            if not current_points:
                actor_cursor.SetVisibility(False)
                return

            max_index = len(current_points) - 1
            if etat_visu["current_point_index"] > max_index:
                etat_visu["current_point_index"] = max_index

            point_x, point_y, point_z = current_points[etat_visu["current_point_index"]]
            point_cursor.SetPoint(0, point_x, point_y, point_z)
            point_cursor.Modified()
            point_cursor_polydata.Modified()
            actor_cursor.SetVisibility(True)

        def get_next_distinct_point_index(current_points, start_index, direction):
            """Retourne l'index du prochain point distinct en sautant les doublons consecutifs."""
            candidate_index = start_index + direction
            while 0 <= candidate_index < len(current_points):
                if current_points[candidate_index] != current_points[start_index]:
                    return candidate_index
                candidate_index += direction
            return start_index

        # Fonctions de navigation
        def visu_actor_list(index):

            # Boucle sur tous les actors work et rapid pour basculer leur visibilite
            for i, actor_toolpath in enumerate(actors_list):
                is_visible = (i == index)
                actor_toolpath.SetVisibility(is_visible)

                # Mise a jour du texte
                if is_visible:
                    update_cursor_actor()
                    update_toolpath_text()

            render_window.Render()

        # Basculer la visibilite actor unique (ici uniquement l'acteur stl)
        def visu_actors_uniq(actor):
            actor.SetVisibility(not actor.GetVisibility())
            render_window.Render()

        # Basculer la visibilite de tous les actors
        def visu_tout():

            etat_visu["all_visible"] = not etat_visu["all_visible"]
            actor_cursor.SetVisibility(False)

            # Boucle sur tous les actors work et rapid pour basculer leur visibilite
            for actor_toolpath in actors_list:
                actor_toolpath.SetVisibility(etat_visu["all_visible"])

            # Mise a jour du texte
            if etat_visu["all_visible"]:
                text.SetInput(text_rendu + "toutes trajectoires affichees")
            else:
                text.SetInput(text_rendu + "toutes trajectoires masquees")

            render_window.Render()

        # Appui clavier
        def appui_clavier(obj, event):

            # Var touche
            touche = obj.GetKeySym()

            # Suivant touche
            # Defilement des toolpath (par bloc ebauche et finition)
            if touche == "Right":
                if etat_visu["current_index"] < len(actors_list) - 1:
                    etat_visu["current_index"] += 1
                    etat_visu["current_point_index"] = 0
                    visu_actor_list(etat_visu["current_index"])

            elif touche == "Left":
                if etat_visu["current_index"] > 0:
                    etat_visu["current_index"] -= 1
                    etat_visu["current_point_index"] = 0
                    visu_actor_list(etat_visu["current_index"])

            elif touche == "Down":
                current_actor_index = etat_visu["current_index"]
                if current_actor_index >= 0 and current_actor_index < len(toolpath_points):
                    next_index = get_next_distinct_point_index(
                        toolpath_points[current_actor_index],
                        etat_visu["current_point_index"],
                        1,
                    )
                    if next_index != etat_visu["current_point_index"]:
                        etat_visu["current_point_index"] = next_index
                        update_cursor_actor()
                        update_toolpath_text()
                        render_window.Render()

            elif touche == "Up":
                if etat_visu["current_index"] >= 0 and etat_visu["current_point_index"] > 0:
                    previous_index = get_next_distinct_point_index(
                        toolpath_points[etat_visu["current_index"]],
                        etat_visu["current_point_index"],
                        -1,
                    )
                    if previous_index != etat_visu["current_point_index"]:
                        etat_visu["current_point_index"] = previous_index
                    else:
                        return
                    update_cursor_actor()
                    update_toolpath_text()
                    render_window.Render()

            # Masquer ou afficher tous les actors de traj
            elif touche == "Escape":
                visu_tout()
                etat_visu["current_index"] = -1
                etat_visu["current_point_index"] = 0

            # Masquer ou afficher le stl
            elif touche == "space":
                visu_actors_uniq(actor_stl)
        
        # Interacteur pour naviguer en 3D
        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(render_window)
        interactor.AddObserver("KeyPressEvent", appui_clavier)

         # Supprimer les lumieres automatiques
        renderer_pc.AutomaticLightCreationOff()
        renderer_pc.RemoveAllLights()
        renderer_toolpath.AutomaticLightCreationOff()
        renderer_toolpath.RemoveAllLights()

        # Creer une lumiere fixe dans la scene
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPositional(True)
        light.SetPosition(100, 100, 100)     # Position fixe
        light.SetFocalPoint(0, 0, 0)         # Elle regarde le centre
        light.SetColor(1.0, 1.0, 1.0)
        light.SetIntensity(0.8)
        renderer_pc.AddLight(light)

        # Mise a jour lumiere (position relative a la camera)
        def update_light_coupled_to_camera(caller, event):
            camera = renderer_pc.GetActiveCamera()
            cam_pos = camera.GetPosition()
            cam_fp = camera.GetFocalPoint()
            light.SetPosition(cam_pos)
            light.SetFocalPoint(cam_fp)

        # Observer sur mouvement de camera
        renderer_pc.GetActiveCamera().AddObserver("ModifiedEvent", update_light_coupled_to_camera)

        # Mettre a jour les donnees et rendre
        renderer_toolpath.ResetCamera() # Recentre la scene sur le toolpath
        render_window.Render()
        interactor.Initialize()

        # Boussole en bas a droite
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(
            self.toolpath_parameters.viewer_compass_size,
            self.toolpath_parameters.viewer_compass_size,
            self.toolpath_parameters.viewer_compass_size,
        )  # Longueur des axes XYZ
        axes.AxisLabelsOn() # Affiche XYZ
        orientation_widget = vtk.vtkOrientationMarkerWidget()
        orientation_widget.SetOrientationMarker(axes)
        orientation_widget.SetInteractor(interactor)
        orientation_widget.SetViewport(0.8, 0.0, 1.0, 0.2) # Position boussole
        orientation_widget.SetEnabled(1)
        orientation_widget.InteractiveOff() # Non cliquable

        # Start
        interactor.Start()
