#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify

import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtk import vtkXMLUnstructuredGridReader
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderWindowInteractor,
    vtkProperty,
    vtkRenderer,
    vtkRenderWindow
)

def vtk_viewer():
    CURRENT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

    # -----------------------------------------------------------------------------
    # VTK pipeline
    # -----------------------------------------------------------------------------

    colors = vtkNamedColors()

    # Read the source file.
    reader = vtkXMLUnstructuredGridReader()
    reader.SetFileName(os.path.join(CURRENT_DIRECTORY, "../exemplos/simplexos.vtu"))
    reader.Update()
    output = reader.GetOutput()
    # scalar_range = output.GetScalarRange()

    mapper = vtkDataSetMapper()
    mapper.SetInputData(output)
    # mapper.SetScalarRange(scalar_range)
    mapper.ScalarVisibilityOff()

    # Create the Actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetLineWidth(2.0)
    actor.GetProperty().SetColor(colors.GetColor3d("MistyRose"))

    backface = vtkProperty()
    backface.SetColor(colors.GetColor3d('Tomato'))
    actor.SetBackfaceProperty(backface)

    # Create the Renderer
    renderer = vtkRenderer()
    renderWindow = vtkRenderWindow()
    renderWindow.AddRenderer(renderer)

    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    renderer.AddActor(actor)
    renderer.SetBackground(colors.GetColor3d('Wheat'))
    renderer.ResetCamera()

    return renderWindow
