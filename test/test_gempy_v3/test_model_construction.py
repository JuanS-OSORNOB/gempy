﻿import pooch
import gempy as gp
from gempy import GeoModel
from gempy.API.io_API import read_orientations, read_surface_points
from gempy.core.data.orientations import Orientations
from gempy.core.data.structural_element import StructuralElement
from gempy.core.data.structural_frame import StructuralFrame
from gempy.core.data.structural_group import Stack
from gempy.core.data.surface_points import SurfacePoints

"""
- [x] create data
- [x] map series
- [ ] plot data
- [ ] compute
- [ ] plot results

"""


def test_read_input_points():
    data_path = 'https://raw.githubusercontent.com/cgre-aachen/gempy_data/master/'
    surface_points_file = pooch.retrieve(
        url=data_path + "data/input_data/jan_models/model1_surface_points.csv",
        known_hash="6f1a39ed77e87a4057f03629c946b1876b87e24409cadfe0e1cf7ab1488f69e4"
    )

    orientations_file = pooch.retrieve(
        url=data_path + "data/input_data/jan_models/model1_orientations.csv",
        known_hash="04c307ae23f70252fe54144a2fb95ca7d96584a2d497ea539ed32dfd23e7cd5d"
    )

    print(pooch.file_hash(surface_points_file))
    print(pooch.file_hash(orientations_file))

    surface_points: SurfacePoints = read_surface_points(
        path=surface_points_file,
    )

    orientations: Orientations = read_orientations(
        path=orientations_file
    )

    return surface_points, orientations


def test_create_grid() -> gp.Grid:
    grid: gp.Grid = gp.Grid(
        extent=[0, 1000, 0, 1000, 0, 1000],
        resolution=[50, 50, 50]
    )
    
    return grid


def test_create_structural_frame() -> StructuralFrame:
    # * Structural elements
    surface_points, orientations = test_read_input_points()
    surface_points_groups = surface_points.get_surface_points_by_id_groups()
    orientations_groups = orientations.get_orientations_by_id_groups()

    structural_elements = []
    for i in range(len(surface_points_groups)):
        # TODO: Split surface points and orientations by id
        structural_element: StructuralElement = StructuralElement(
            name="layer1",
            surface_points=surface_points_groups[i],
            orientations=orientations_groups[i],
            color="#000000"
        )

        structural_elements.append(structural_element)

    # * Structural groups definitions
    default_formation: Stack = Stack(
        name="default_formation",
        elements=structural_elements
    )

    # ? Should I move this to the constructor?
    structural_frame: StructuralFrame = StructuralFrame(
        structural_groups=[default_formation],
        structural_elements=structural_elements
    )

    return structural_frame


def test_create_interpolation_options() -> gp.InterpolationOptions:
    
    interpolation_options: gp.InterpolationOptions = gp.InterpolationOptions(
        range=1,
        c_o=1,
    )
    
    return interpolation_options
    


def test_create_geomodel() -> GeoModel:
    geo_model: GeoModel = GeoModel(
        name="horizontal",
        structural_frame=test_create_structural_frame(),
        grid=test_create_grid(),
        interpolation_options = test_create_interpolation_options()
    )
    
    return geo_model


def test_get_surface_df():
    geo_model = test_create_geomodel()
    surfaces_df = "foo"
    print(surfaces_df)


def test_plot_input():
    geo_model = test_create_geomodel()
    gp.plot_2d(geo_model, direction=['y'])