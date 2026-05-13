# -*- coding: utf-8 -*-

# Librairie standard
import math
import vtk

# Modules internes
from p04_iso_analyzer.iso_interpreter import MoveType
from p01_machines_config.machine_parameters import JsonDict, MachineParameters
from p05_toolpath_constructor.toolpath_builder import ToolPathBuilder


class ToolPathInterpreter:
    """Classe qui permet d'interpeter les datas"""

    def __init__(self, machine_config: JsonDict, channel_name: str, part_thickness):
        # Initialisation des variables
        self.machine = MachineParameters.from_config(machine_config, channel_name)
        self.part_thickness = part_thickness

    @staticmethod
    def _extract_axis_sign(vector):
        """Retourne le signe de l'axe principal d'un vecteur base (ex: [-1,0,0] -> -1)."""
        if not isinstance(vector, list) or len(vector) != 3:
            raise ValueError("VectorFormatError: le vecteur doit contenir 3 composantes")

        non_zero_values = [value for value in vector if value != 0]
        if len(non_zero_values) != 1:
            raise ValueError("VectorFormatError: le vecteur doit avoir une seule composante non nulle")

        sign = non_zero_values[0]
        if sign not in (-1, 1):
            raise ValueError("VectorFormatError: la composante non nulle doit valoir -1 ou 1")
        return sign

    def get_polydata_symmetry_plane_vector(self):
        """Compare ipart/ipath et retourne ipart si inversion (symetrie necessaire)."""
        if self._extract_axis_sign(self.machine.ipartvector) != self._extract_axis_sign(self.machine.ipathvector):
            return {"name": "ipartvector", "vector": self.machine.ipartvector}
        return None

    def analyze(self, list_datas, resolution_cercle):
        """Cette methode recupere les donnees utiles a la construction des trajectoires"""

        # Instanciation des classes
        obj_tool_path_builder = ToolPathBuilder()
        symmetry_plane_vector = self.get_polydata_symmetry_plane_vector()

        # Def structures points et lignes
        points_toolpath = vtk.vtkPoints()
        vertex_toolpath = vtk.vtkCellArray()
        c_values_toolpath = []
        move_type_values = []

        # Outil courant
        current_tool = 0

        # Acteurs
        actors = []
        obj_vtk_functions = VtkFunctions()

        current_polyline_points = []
        current_polyline_c_values = []
        current_move_group_type = None

        def build_rotated_path(path_points, previous_c, current_c):
            """Construit la trajectoire en forcant d'abord la rotation du point courant si C change."""
            if len(path_points) < 2:
                return [], []

            if float(current_c) == float(previous_c):
                return list(path_points), [float(current_c)] * len(path_points)

            # Quand C change en meme temps qu'un deplacement XYZ, on insere un point
            # duplique au debut pour separer visuellement la rotation du reste du mouvement.
            rotated_path_points = [path_points[0], path_points[0], *path_points[1:]]
            rotated_path_c_values = [float(previous_c), float(current_c), *([float(current_c)] * (len(path_points) - 1))]
            return rotated_path_points, rotated_path_c_values

        def build_c_axis_rotation_path(previous_point, current_point, previous_c, current_c):
            """Construit une trajectoire pure de rotation C sur le point courant."""
            if float(previous_c) == float(current_c):
                return [], []

            pivot_point = (
                float(previous_point[0]),
                float(previous_point[1]),
                float(previous_point[2]),
            )
            return [pivot_point, pivot_point], [float(previous_c), float(current_c)]

        def flush_current_polyline():
            """Ecrit la polyligne courante dans les structures VTK."""
            nonlocal current_polyline_points, current_polyline_c_values, current_move_group_type
            if len(current_polyline_points) < 2 or current_move_group_type is None:
                current_polyline_points = []
                current_polyline_c_values = []
                current_move_group_type = None
                return

            obj_tool_path_builder.create_polyline(points_toolpath, vertex_toolpath, current_polyline_points)
            c_values_toolpath.extend(current_polyline_c_values)
            # Le type de mouvement est porte au niveau cellule : une polyline
            # correspond donc ici a un groupe homogene de segments.
            move_type_values.append(current_move_group_type)
            current_polyline_points = []
            current_polyline_c_values = []
            current_move_group_type = None

        def append_path_to_current_polyline(path_points, path_c_values, move_type_value):
            """Ajoute un segment a la polyligne courante ou force un flush si besoin."""
            nonlocal current_polyline_points, current_polyline_c_values, current_move_group_type
            if len(path_points) < 2:
                return

            if current_move_group_type != move_type_value:
                flush_current_polyline()

            if not current_polyline_points:
                current_polyline_points = list(path_points)
                current_polyline_c_values = list(path_c_values)
                current_move_group_type = move_type_value
                return

            # Si deux segments se touchent deja en extremite, on evite de dupliquer
            # inutilement le point commun dans la polyline finale.
            if current_polyline_points[-1] == path_points[0]:
                current_polyline_points.extend(path_points[1:])
                current_polyline_c_values.extend(path_c_values[1:])
            else:
                current_polyline_points.extend(path_points)
                current_polyline_c_values.extend(path_c_values)

        def finalize_polydata_and_add_actors():
            """Construit le polydata, applique transformations puis cree l'acteur."""
            nonlocal actors
            flush_current_polyline()
            if current_tool == 0 or vertex_toolpath.GetNumberOfCells() == 0:
                return

            poly_data_toolpath = vtk.vtkPolyData()
            poly_data_toolpath.SetPoints(points_toolpath)
            poly_data_toolpath.SetLines(vertex_toolpath)

            # On enrichit ensuite le polydata avec les donnees necessaires au viewer :
            # angle C par point, coordonnees d'origine et type de mouvement par cellule.
            poly_data_toolpath = obj_vtk_functions.add_c_angle_to_polydata(
                poly_data_toolpath,
                c_values_toolpath,
            )
            poly_data_toolpath = obj_vtk_functions.add_original_coordinates_to_polydata(poly_data_toolpath)
            poly_data_toolpath = obj_vtk_functions.add_move_type_to_polydata(
                poly_data_toolpath,
                move_type_values,
            )
            poly_data_toolpath = obj_vtk_functions.apply_c_rotation_to_polydata(poly_data_toolpath)

            # Application symetrie polydata si necessaire
            if symmetry_plane_vector is not None:
                poly_data_toolpath = obj_vtk_functions.apply_symmetry_to_polydata(
                    poly_data_toolpath,
                    symmetry_plane_vector["vector"])

            # Application decalage en Z si epaisseur piece renseignee
            if self.part_thickness != 0:
                poly_data_toolpath = obj_vtk_functions.apply_z_offset_to_polydata(
                    poly_data_toolpath,
                    self.part_thickness)

            # Ajout de l'acteur
            actors = obj_vtk_functions.create_actor(
                poly_data_toolpath,
                actors,
                current_tool)

        # Initialisation previous point
        #previous_point = [self.machine.home_tool_x, self.machine.home_tool_y, self.machine.home_tool_z]

        # Lecture datas
        for current_line in list_datas:

            # Si num outil de la ligne courante <> 0 et le courant = 0
            if current_line.tool_number != 0 and current_tool == 0:
                
                previous_point = [current_line.endpoint_x, current_line.endpoint_y, current_line.endpoint_z]

                # Val outil courant
                current_tool = current_line.tool_number

                # Def structures points et lignes
                points_toolpath = vtk.vtkPoints()
                vertex_toolpath = vtk.vtkCellArray()
                c_values_toolpath = []
                move_type_values = []
                current_polyline_points = []
                current_polyline_c_values = []
                current_move_group_type = None

            # Si nouvel outil
            if current_line.tool_number != current_tool and current_line.tool_number != 0:
                finalize_polydata_and_add_actors()

                # Redef structures points et lignes
                points_toolpath = vtk.vtkPoints()
                vertex_toolpath = vtk.vtkCellArray()
                c_values_toolpath = []
                move_type_values = []
                current_polyline_points = []
                current_polyline_c_values = []
                current_move_group_type = None

                previous_point = [current_line.endpoint_x, current_line.endpoint_y, current_line.endpoint_z]

                # Val outil courant
                current_tool = current_line.tool_number

                # Initialisation du point hometool
                #previous_point = [self.machine.home_tool_x, self.machine.home_tool_y, self.machine.home_tool_z]

            # Si ligne avec outil courant
            if current_line.tool_number != 0:
                current_point = [current_line.endpoint_x, current_line.endpoint_y, current_line.endpoint_z, current_line.endpoint_c]
                previous_c = float(previous_point[3]) if len(previous_point) > 3 else 0.0
                current_c = float(current_point[3])

                # Si changement d'angle C sans deplacement XYZ, on construit une trajectoire de rotation pure sur place pour visualiser la transition.
                if current_c != previous_c and current_line.distance == 0.0 and current_line.distance_in_material == 0.0:
                    path_points, path_c_values = build_c_axis_rotation_path(previous_point, current_point, previous_c, current_c)
                    if current_line.move_type == MoveType.LINEAR_MOVE:
                        append_path_to_current_polyline(path_points, path_c_values, 1)
                    else:
                        append_path_to_current_polyline(path_points, path_c_values, 0)

            # Si distance parcourue
            if current_line.distance != 0.0 or current_line.distance_in_material != 0.0 and current_line.tool_number != 0:

                # Si ligne en avance rapide
                if current_line.move_type == MoveType.RAPID_MOVE:
                    base_path_points = obj_tool_path_builder.build_line_points(previous_point, current_point)
                    path_points, path_c_values = build_rotated_path(base_path_points, previous_c, current_c)
                    append_path_to_current_polyline(path_points, path_c_values, 0)

                # Si ligne en avance travail
                elif current_line.move_type == MoveType.LINEAR_MOVE:
                    base_path_points = obj_tool_path_builder.build_line_points(previous_point, current_point)
                    path_points, path_c_values = build_rotated_path(base_path_points, previous_c, current_c)
                    append_path_to_current_polyline(path_points, path_c_values, 1)

                # Si cercle CW
                elif current_line.move_type == MoveType.CIRCULAR_MOVE_CW:
                    base_path_points = obj_tool_path_builder.build_circle_points(
                        previous_point,
                        current_point,
                        current_line.radius,
                        resolution_cercle,
                        True,
                        current_line.work_plane)
                    path_points, path_c_values = build_rotated_path(base_path_points, previous_c, current_c)
                    append_path_to_current_polyline(path_points, path_c_values, 1)

                # Si cercle CCW
                elif current_line.move_type == MoveType.CIRCULAR_MOVE_CCW:
                    base_path_points = obj_tool_path_builder.build_circle_points(
                        previous_point,
                        current_point,
                        current_line.radius,
                        resolution_cercle,
                        False,
                        current_line.work_plane)
                    path_points, path_c_values = build_rotated_path(base_path_points, previous_c, current_c)
                    append_path_to_current_polyline(path_points, path_c_values, 1)

            # Mise a jour previous point si ligne avec outil courant, y compris pour un mouvement C pur sans distance XYZ
            if current_line.tool_number != 0:
                # Recup pt precedent, y compris pour un mouvement C pur sans distance XYZ
                previous_point = current_point

        finalize_polydata_and_add_actors()
        return actors


class VtkFunctions:
    """Classe qui regroupe des fonctions pour vtk"""

    def __init__(self):
        pass

    def apply_symmetry_to_polydata(self, polydata, plane_vector):
        """Applique une symetrie a un vtkPolyData selon le plan donne."""
        axis = [abs(value) for value in plane_vector]

        if axis == [1, 0, 0]:
            scale = (-1, 1, 1)
        elif axis == [0, 1, 0]:
            scale = (1, -1, 1)
        elif axis == [0, 0, 1]:
            scale = (1, 1, -1)
        else:
            raise ValueError("SymmetryError: vecteur de plan non supporte")

        transform = vtk.vtkTransform()
        transform.Scale(scale[0], scale[1], scale[2])

        transform_filter = vtk.vtkTransformPolyDataFilter()
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(polydata)
        transform_filter.Update()

        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(transform_filter.GetOutput())
        return output_polydata

    def add_c_angle_to_polydata(self, polydata, c_values, array_name="C_angle_deg"):
        """Ajoute un tableau PointData contenant l'angle C de chaque point."""
        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(polydata)

        num_points = output_polydata.GetNumberOfPoints()
        if len(c_values) != num_points:
            raise ValueError("CDataError: nombre d'angles C different du nombre de points")

        c_array = vtk.vtkDoubleArray()
        c_array.SetName(array_name)
        c_array.SetNumberOfComponents(1)
        c_array.SetNumberOfTuples(num_points)

        for i, c_value in enumerate(c_values):
            c_array.SetValue(i, float(c_value))

        output_polydata.GetPointData().AddArray(c_array)
        return output_polydata

    def add_original_coordinates_to_polydata(self, polydata):
        """Ajoute les coordonnees d'origine avant transformation dans le PointData."""
        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(polydata)

        num_points = output_polydata.GetNumberOfPoints()
        original_x_array = vtk.vtkDoubleArray()
        original_y_array = vtk.vtkDoubleArray()
        original_z_array = vtk.vtkDoubleArray()
        original_x_array.SetName("OriginalX")
        original_y_array.SetName("OriginalY")
        original_z_array.SetName("OriginalZ")
        original_x_array.SetNumberOfComponents(1)
        original_y_array.SetNumberOfComponents(1)
        original_z_array.SetNumberOfComponents(1)
        original_x_array.SetNumberOfTuples(num_points)
        original_y_array.SetNumberOfTuples(num_points)
        original_z_array.SetNumberOfTuples(num_points)

        for i in range(num_points):
            point_x, point_y, point_z = output_polydata.GetPoint(i)
            original_x_array.SetValue(i, float(point_x))
            original_y_array.SetValue(i, float(point_y))
            original_z_array.SetValue(i, float(point_z))

        output_polydata.GetPointData().AddArray(original_x_array)
        output_polydata.GetPointData().AddArray(original_y_array)
        output_polydata.GetPointData().AddArray(original_z_array)
        return output_polydata

    def add_move_type_to_polydata(self, polydata, move_type_values, array_name="MoveType"):
        """Ajoute un tableau CellData contenant le type de mouvement de chaque segment."""
        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(polydata)

        num_cells = output_polydata.GetNumberOfCells()
        if len(move_type_values) != num_cells:
            raise ValueError("MoveTypeDataError: nombre de types de mouvements different du nombre de cellules")

        move_type_array = vtk.vtkUnsignedCharArray()
        move_type_array.SetName(array_name)
        move_type_array.SetNumberOfComponents(1)
        move_type_array.SetNumberOfTuples(num_cells)

        for i, move_type_value in enumerate(move_type_values):
            move_type_array.SetValue(i, int(move_type_value))

        output_polydata.GetCellData().SetScalars(move_type_array)
        return output_polydata

    def apply_c_rotation_to_polydata(self, polydata, array_name="C_angle_deg"):
        """Applique une rotation XY point par point selon le tag C stocke en degres."""
        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(polydata)

        num_points = output_polydata.GetNumberOfPoints()
        if num_points == 0:
            return output_polydata

        c_array = output_polydata.GetPointData().GetArray(array_name)
        if c_array is None:
            return output_polydata

        rotated_points = vtk.vtkPoints()
        rotated_points.SetNumberOfPoints(num_points)

        for i in range(num_points):
            x_value, y_value, z_value = output_polydata.GetPoint(i)
            c_value = c_array.GetValue(i)
            c_rad = math.radians(-c_value)
            x_rotated = x_value * math.cos(c_rad) - y_value * math.sin(c_rad)
            y_rotated = x_value * math.sin(c_rad) + y_value * math.cos(c_rad)
            rotated_points.SetPoint(i, x_rotated, y_rotated, z_value)

        output_polydata.SetPoints(rotated_points)
        return output_polydata

    def apply_z_offset_to_polydata(self, polydata, offset_z):
        """Applique un decalage de toutes les coordonnees selon Z."""
        transform = vtk.vtkTransform()
        transform.Translate(0, 0, offset_z)

        transform_filter = vtk.vtkTransformPolyDataFilter()
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(polydata)
        transform_filter.Update()

        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(transform_filter.GetOutput())
        return output_polydata

    def create_actor(self, toolpath_data, actors_list, current_tool):
        """Cette methode sert a creer un acteur de trajectoire pour un outil."""
        mapper_toolpath = vtk.vtkPolyDataMapper()
        mapper_toolpath.SetInputData(toolpath_data)
        mapper_toolpath.SetScalarModeToUseCellData()
        mapper_toolpath.SetColorModeToMapScalars()

        actor_toolpath = vtk.vtkActor()
        actor_toolpath.SetMapper(mapper_toolpath)
        actor_toolpath.tag = current_tool

        actors_list.append(actor_toolpath)
        return actors_list
