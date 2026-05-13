# -*- coding: utf-8 -*-

import math


def line_circle_intersections_2d(line_start_u, line_start_v, line_end_u, line_end_v, center_u, center_v, radius):
    """Retourne les intersections entre une droite 2D et un cercle sous forme (t, u, v)."""
    # Vecteur directeur de la droite dans le repere 2D du plan courant.
    delta_u = line_end_u - line_start_u
    delta_v = line_end_v - line_start_v
    # Position du point de depart de la droite relativement au centre du cercle.
    offset_u = line_start_u - center_u
    offset_v = line_start_v - center_v
    # La droite est parametree par P(t) = start + t * delta.
    # En injectant cette expression dans l'equation du cercle, on obtient un
    # polynome du second degre en t.
    quadratic_a = delta_u ** 2 + delta_v ** 2
    quadratic_b = 2 * (offset_u * delta_u + offset_v * delta_v)
    quadratic_c = offset_u ** 2 + offset_v ** 2 - radius ** 2
    discriminant = quadratic_b ** 2 - 4 * quadratic_a * quadratic_c
    # Pas d'intersection si la droite est degeneree ou si le discriminant est negatif.
    if quadratic_a == 0 or discriminant < 0:
        return []
    # Un seul point si la droite est tangente au cercle.
    if abs(discriminant) <= 1e-9:
        parameter_t = -quadratic_b / (2 * quadratic_a)
        return [(parameter_t, line_start_u + parameter_t * delta_u, line_start_v + parameter_t * delta_v)]
    # Deux points si la droite coupe le cercle.
    sqrt_discriminant = math.sqrt(discriminant)
    parameter_t1 = (-quadratic_b - sqrt_discriminant) / (2 * quadratic_a)
    parameter_t2 = (-quadratic_b + sqrt_discriminant) / (2 * quadratic_a)
    return [
        (parameter_t1, line_start_u + parameter_t1 * delta_u, line_start_v + parameter_t1 * delta_v),
        (parameter_t2, line_start_u + parameter_t2 * delta_u, line_start_v + parameter_t2 * delta_v),
    ]


def project_point_to_plane(work_plane: str, point_x: float, point_y: float, point_z: float) -> tuple[float, float]:
    """Projette un point 3D dans le plan de travail pour les calculs 2D."""
    # On travaille ensuite dans un repere local (u, v) adapte au plan choisi.
    # Le but est d'avoir les memes calculs 2D quelle que soit l'orientation
    # de l'arc dans l'espace machine.
    if work_plane == "XY":
        return point_x, point_y
    if work_plane == "XZ":
        return point_x, point_z
    return point_y, point_z


def build_point_from_plane(work_plane: str, plane_u: float, plane_v: float, constant_value: float) -> tuple[float, float, float]:
    """Reconstruit un point 3D a partir de coordonnees 2D dans le plan de travail."""
    # constant_value represente la coordonnee hors plan, conservee pendant l'arc.
    # On fait ici l'operation inverse de project_point_to_plane().
    if work_plane == "XY":
        return plane_u, plane_v, constant_value
    if work_plane == "XZ":
        return plane_u, constant_value, plane_v
    return constant_value, plane_u, plane_v


def cw_tangent_vector(work_plane: str, radial_u: float, radial_v: float) -> tuple[float, float]:
    """Retourne la tangente de depart d'un G2 dans le plan considere."""
    # Le vecteur radial pointe du centre vers le point de depart de l'arc.
    # La tangente CW s'obtient par une rotation de ce vecteur dans le sens horaire.
    # Le plan XZ utilise une orientation differente du repere (u, v),
    # d'ou le changement de signe par rapport aux autres plans.
    if work_plane == "XZ":
        return -radial_v, radial_u
    return radial_v, -radial_u


def ccw_tangent_vector(work_plane: str, radial_u: float, radial_v: float) -> tuple[float, float]:
    """Retourne la tangente de depart d'un G3 dans le plan considere."""
    # Meme principe que pour G2, mais avec une rotation anti-horaire
    # du vecteur radial au point de depart.
    # Meme remarque que pour G2 : le plan XZ inverse l'orientation locale.
    if work_plane == "XZ":
        return radial_v, -radial_u
    return -radial_v, radial_u
