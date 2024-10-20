import os
import requests

from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vuetify, vtk as vtk_widgets

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

# -----------------------------------------------------------------------------
# VTK pipeline
# -----------------------------------------------------------------------------

CURRENT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

colors = vtkNamedColors()

# url = "http://backend_old:8080/api/download/volume-interno"
# response = requests.get(url)

# if response.status_code == 200:
#     with open(os.path.join(CURRENT_DIRECTORY, "../exemplos/simplexos.vtu"), "wb") as f:
#         f.write(response.content)
#     print("File downloaded successfully!")
# else:
#     print("Failed to download the file.")

# Read the source file.
reader = vtkXMLUnstructuredGridReader()
# reader.SetFileName(os.path.join(CURRENT_DIRECTORY, "../exemplos/simplexos.vtu"))
reader.SetFileName(os.path.join(CURRENT_DIRECTORY, "vtu_files/simplexos.vtu"))
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

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

# -----------------------------------------------------------------------------
# Web App setup
# -----------------------------------------------------------------------------

# Função que será chamada ao clicar no botão de submit
def submit_form():
    funcao_externa = state.funcao_externa
    funcao_interna = state.funcao_interna
    tamanho_dominio = state.tamanho_dominio
    nivel_refinamento = state.nivel_refinamento
    qnt_blocos_zero = state.qnt_blocos_zero

    with open("/deploy/server/logs/log.txt", "a") as file:
        file.write(f"tamanho_dominio = {tamanho_dominio}\n")


with SinglePageWithDrawerLayout(server) as layout:

    with layout.drawer:
        vuetify.VSelect(
            label="Função Implícita Externa",
            v_model=("funcao_externa", "Coração"),
            items=("options_funcao_externa", [
                "Coração",
                "Esfera Maior",
                "Esfera Menor",
                "Torus",
                "3-Torus",
            ]),
        )
        vuetify.VSelect(
            label="Função Implícita Interna",
            v_model=("funcao_interna", "-"),
            items=("options_funcao_interna", [
                "-",
                "Coração",
                "Esfera Maior",
                "Esfera Menor",
                "Torus",
                "3-Torus",
            ]),
        )

        vuetify.VTextField(
            label="Tamanho do Domínio",
            v_model=("tamanho_dominio", 3),
            type="number"
        )
        vuetify.VTextField(
            label="Nível Máximo de Refinamento",
            v_model=("nivel_refinamento", 2),
            type="number"
        )
        vuetify.VTextField(
            label="Quantidade de Blocos Nível Zero",
            v_model=("qnt_blocos_zero", 2),
            type="number"
        )

        vuetify.VBtn("Gerar malha", click=submit_form)

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height", ):
            view = vtk_widgets.VtkLocalView(renderWindow)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()