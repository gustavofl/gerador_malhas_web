import os
import requests
import json
import tarfile
from datetime import datetime
import pytz
import asyncio
import inspect

from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vuetify, vtk as vtk_widgets

import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2
from vtk import (
    vtkNamedColors,
    vtkXMLUnstructuredGridReader,
    vtkActor,
    vtkDataSetMapper,
    vtkRenderWindowInteractor,
    vtkProperty,
    vtkRenderer,
    vtkRenderWindow,
    vtkPlane,
    vtkCutter,
    vtkGeometryFilter,
    vtkClipPolyData,
    vtkPolyDataMapper,
)

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------

CURRENT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

URL_API="http://gerador-old:8080"
LOG_FILE="/deploy/api.log"
LOCAL_TIMEZONE="America/Recife"

EXEMPLO_VTU_EXTERNO="/deploy/vtu_files/example/malha_externa.vtu"
EXEMPLO_VTU_INTERNO="/deploy/vtu_files/example/malha_interna.vtu"

# -----------------------------------------------------------------------------
# utils
# -----------------------------------------------------------------------------

def log(mensagem):
    utc_now = datetime.now()
    fuso_horario = pytz.timezone(LOCAL_TIMEZONE)
    timestamp_local = utc_now.replace(tzinfo=pytz.utc).astimezone(fuso_horario)
    timestamp_local_str = timestamp_local.strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a") as file:
        file.write(f"[{timestamp_local_str}] {mensagem}\n")

# -----------------------------------------------------------------------------
# VTK pipeline
# -----------------------------------------------------------------------------

colors = vtkNamedColors()

# Create the Renderer
renderer = vtkRenderer()
renderWindow = vtkRenderWindow()
renderWindow.AddRenderer(renderer)

renderWindowInteractor = vtkRenderWindowInteractor()
renderWindowInteractor.SetRenderWindow(renderWindow)
renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

malha1 = None
malha2 = None

class Malha:
    def __init__(self):
        self.actors = []
        self.vtu_grid_reader = None

        self.clipper = None
        self.cutter = None
        self.plane = None

        self.invert_clip_x = False
        self.clip_x = False

    def load_vtu_file(self, nome_arquivo_malha):
        self.vtu_grid_reader = vtkXMLUnstructuredGridReader()
        self.vtu_grid_reader.SetFileName(nome_arquivo_malha)
        self.vtu_grid_reader.Update()

    def gerar_malha_sem_cortes(self):
        self.deletar_actors()
        self.clip_x = False

        mapper = vtkDataSetMapper()
        mapper.SetInputData(self.vtu_grid_reader.GetOutput())
        mapper.ScalarVisibilityOff()

        backface = vtkProperty()
        backface.SetColor(colors.GetColor3d('Tomato'))

        # Create the Actor
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().EdgeVisibilityOn()
        actor.GetProperty().SetLineWidth(2.0)
        actor.GetProperty().SetColor(colors.GetColor3d("MistyRose"))
        actor.SetBackfaceProperty(backface)

        self.actors = [actor]
    
    def gerar_malha_corte_x(self):
        self.deletar_actors()
        self.clip_x = True

        # cores
        backProp = vtkProperty()
        backProp.SetColor(colors.GetColor3d('Tomato'))

        cor_malha = colors.GetColor3d('MistyRose')

        # plano de corte
        self.plane = vtkPlane()
        self.plane.SetOrigin(0, 0, 0)
        self.plane.SetNormal(1, 0, 0)

        # mostrando fatia visivel da malha

        vtuFilter = vtkGeometryFilter()
        vtuFilter.SetInputConnection(self.vtu_grid_reader.GetOutputPort())

        self.clipper = vtkClipPolyData()
        self.clipper.SetInputConnection(vtuFilter.GetOutputPort())
        self.clipper.SetClipFunction(self.plane)
        self.clipper.GenerateClipScalarsOn()
        self.clipper.GenerateClippedOutputOn()
        self.clipper.SetValue(0)

        clipMapper = vtkPolyDataMapper()
        clipMapper.SetInputConnection(self.clipper.GetClippedOutputPort())
        clipMapper.ScalarVisibilityOff()

        clipActor = vtkActor()
        clipActor.SetMapper(clipMapper)
        clipActor.GetProperty().SetColor(cor_malha)
        clipActor.GetProperty().EdgeVisibilityOn()
        clipActor.GetProperty().SetLineWidth(2.0)
        clipActor.SetBackfaceProperty(backProp)

        # mostrando plano de corte

        self.cutter = vtkCutter()
        self.cutter.SetInputConnection(self.vtu_grid_reader.GetOutputPort())
        self.cutter.SetCutFunction(self.plane)
        self.cutter.GenerateCutScalarsOn()
        self.cutter.SetValue(0, 0)
        self.cutter.Update()

        mapperCut0 = vtkDataSetMapper()
        mapperCut0.SetInputData(self.cutter.GetOutput())
        mapperCut0.ScalarVisibilityOff()

        CutActor0 = vtkActor()
        CutActor0.SetMapper(mapperCut0)
        CutActor0.GetProperty().SetColor(cor_malha)
        CutActor0.GetProperty().EdgeVisibilityOn()
        CutActor0.GetProperty().SetLineWidth(2.0)
        CutActor0.SetBackfaceProperty(backProp)

        self.actors = [
            clipActor,
            CutActor0
        ]
    
    def change_offset_x(self, offset_x):
        if(self.clip_x):
            self.plane.SetOrigin(offset_x, 0, 0)
            self.cutter.Update()
    
    def change_direc_cut_x(self, invert):
        if(self.clip_x):
            mult_invert = 1
            if(invert):
                mult_invert = -1
            
            self.plane.SetNormal(mult_invert, 0, 0)

    def deletar_actors(self):
        for actor in self.actors:
            del actor
        self.actors = []
    
    def set_visibility(self, visivel):
        for actor in self.actors:
            actor.SetVisibility(visivel)

    def get_actors(self):
        return self.actors

def gerar_view():
    global malha1, malha2

    for actor in renderer.GetActors():
        renderer.RemoveActor(actor)

    if(malha1 == None): malha1 = Malha()
    if(malha2 == None): malha2 = Malha()

    malha1.load_vtu_file(state.lista_arquivos_malhas[0])
    malha2.load_vtu_file(state.lista_arquivos_malhas[1])

    # malha1.gerar_malha_sem_cortes()
    # malha2.gerar_malha_sem_cortes()

    malha1.gerar_malha_corte_x()
    malha2.gerar_malha_corte_x()

    for actor in malha1.get_actors(): renderer.AddActor(actor)
    for actor in malha2.get_actors(): renderer.AddActor(actor)

    renderer.SetBackground(colors.GetColor3d('Wheat'))
    renderer.ResetCamera()

# -----------------------------------------------------------------------------
# backend connection
# -----------------------------------------------------------------------------

# Função para consultar o progresso da API
def consultar_progresso():
    try:
        token = state.token

        data = {
            'token': token,
        }

        response = requests.post(f"{URL_API}/api/status", data=data)

        if response.status_code == 200:
            progresso = float(response.json().get("progresso", 0))

            return progresso
        else:
            log(f"Erro ao enviar dados ao servidor. [Código {response.status_code}: {response.text}]")
    except requests.RequestException:
        log("Erro ao consultar o progresso")
    except Exception as error:
        nome_funcao = inspect.currentframe().f_code.co_name
        log(f"Erro nao identificado em {nome_funcao}. [{repr(error)}]")
    
    return 0

# Função que será chamada ao clicar no botão de submit
def submit_form():
    map_parametros = {
        "-":"-",
        "Coração":"coracao",
        "Esfera Maior":"esfera2",
        "Esfera Menor":"esfera",
        "Torus":"torus",
        "3-Torus":"3torus"
    }

    try:
        funcao_externa = map_parametros[state.funcao_externa]
        funcao_interna = map_parametros[state.funcao_interna]
        tamanho_dominio = state.tamanho_dominio
        nivel_refinamento = state.nivel_refinamento
        qnt_blocos_zero = state.qnt_blocos_zero

        data = {
            'funcao_externa': funcao_externa,
            'funcao_interna': funcao_interna,
            'tamanho_dominio': tamanho_dominio,
            'nivel_refinamento': nivel_refinamento,
            'qnt_blocos_zero': qnt_blocos_zero,
            'token': state.token,
        }

        response = requests.post(f"{URL_API}/api/run", data=data)

        if response.status_code == 200:
            state.token = json.loads(response.text)['token']
            state.progresso = 0
            state.monitorar_progresso = True

            log(f"Solicitacao de geracao de malha realizada com sucesso.")
        else:
            log(f"Erro ao enviar dados ao servidor.[Código {response.status_code}: {response.text}]")
    except Exception as error:
        nome_funcao = inspect.currentframe().f_code.co_name
        log(f"Erro nao identificado em {nome_funcao}. [{repr(error)}]")

# Função para baixar as malhas geradas
def get_malhas():
    try:
        token = state.token

        data = {
            'token': token,
        }

        response = requests.post(f"{URL_API}/api/download", data=data)

        if response.status_code == 200:
            dir_token = f'/deploy/vtu_files/tmp_data/{token}'

            os.makedirs(dir_token, exist_ok=True)

            nome_arquivo_tar = f'malhas.tar.gz'
            nome_completo_arquivo_tar = f"{dir_token}/{nome_arquivo_tar}"

            with open(nome_completo_arquivo_tar, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            with tarfile.open(nome_completo_arquivo_tar, 'r:gz') as tar:
                tar.extractall(path=dir_token)

            state.lista_arquivos_malhas[0] = f'{dir_token}/simplexos_externos.vtu'

            state.lista_arquivos_malhas[1] = f'{dir_token}/simplexos_internos.vtu'

            log(f"Malhas baixadas com sucesso.")
        else:
            log(f"Erro ao baixar dados do servidor. [Código {response.status_code}: {response.text}]")
    except Exception as error:
        nome_funcao = inspect.currentframe().f_code.co_name
        log(f"Erro nao identificado em {nome_funcao}. [{repr(error)}]")

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

state.malha1_visivel = True
state.malha2_visivel = True

state.lista_arquivos_malhas = [
    EXEMPLO_VTU_EXTERNO,
    EXEMPLO_VTU_INTERNO
]

state.token = None

# -----------------------------------------------------------------------------
# Background thread
# -----------------------------------------------------------------------------

fator_progresso_geracao = 0.95

async def atualizar_progresso(**kwargs):
    while True:
        with state:
            if(state.monitorar_progresso):
                if(state.progresso < 100*fator_progresso_geracao):
                    progresso_geracao = consultar_progresso()

                    state.progresso = progresso_geracao * fator_progresso_geracao
                
                elif(state.progresso == 100*fator_progresso_geracao):
                    get_malhas()

                    state.progresso = 100

                    state.monitorar_progresso = False

            if(state.remover_task):
                ctrl.remove(atualizar_progresso)
    
        await asyncio.sleep(1)


ctrl.on_server_ready.add_task(atualizar_progresso)


# -----------------------------------------------------------------------------
# Web App setup
# -----------------------------------------------------------------------------

def atualizar_malhas():
    gerar_view()
    state.malha1_visivel = True
    state.malha2_visivel = True
    ctrl.view_update()

@state.change("malha1_visivel")
def update_visibilidade_malha1(malha1_visivel, **kwargs):
    malha1.set_visibility(malha1_visivel)
    ctrl.view_update()

@state.change("malha2_visivel")
def update_visibilidade_malha2(malha2_visivel, **kwargs):
    malha2.set_visibility(malha2_visivel)
    ctrl.view_update()

@state.change("progresso")
def ativar_btn_regarregar(progresso, **kwargs):
    if(progresso == 100):
        state.desabilitar_recarregar = False
    else:
        state.desabilitar_recarregar = True

@state.change("offset_clip_x")
def update_offset_cut_x(offset_clip_x, **kwargs):
    malha1.change_offset_x(offset_clip_x)
    malha2.change_offset_x(offset_clip_x)
    ctrl.view_update()

@state.change("invert_clip_x")
def update_direc_cut_x(invert_clip_x, **kwargs):
    malha1.change_direc_cut_x(invert_clip_x)
    malha2.change_direc_cut_x(invert_clip_x)
    ctrl.view_update()

with SinglePageWithDrawerLayout(server) as layout:

    with layout.drawer:
        with vuetify.VContainer(fluid=True, classes="pa-2", ):
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
                v_model=("nivel_refinamento", 3),
                type="number"
            )
            vuetify.VTextField(
                label="Quantidade de Blocos Nível Zero",
                v_model=("qnt_blocos_zero", 4),
                type="number"
            )

            with vuetify.VRow(classes="justify-center"):
                vuetify.VBtn("Gerar malha", click=submit_form, color="blue")

            with vuetify.VRow(classes="justify-center mt-5"):
                vuetify.VProgressCircular(
                    v_model=("progresso", 0),
                    color="green",
                    size=28,
                    width=8,
                    classes="my-auto mx-3",
                    label="teste",
                )

                vuetify.VBtn(
                    "Recarregar", 
                    click=atualizar_malhas, 
                    disabled=("desabilitar_recarregar", True),
                    color="green",
                )

            vuetify.VDivider(classes="mt-5")

            vuetify.VContainer("Visibilidade das Malhas", classes="text-h6 text-center")

            vuetify.VCheckbox(
                v_model=("malha1_visivel", True),
                on_icon="mdi-cube-outline",
                off_icon="mdi-cube-off-outline",
                classes="mx-1",
                hide_details=True,
                dense=True,
                label="Malha Externa",
            )

            vuetify.VCheckbox(
                v_model=("malha2_visivel", True),
                on_icon="mdi-cube-outline",
                off_icon="mdi-cube-off-outline",
                classes="mx-1",
                hide_details=True,
                dense=True,
                label="Malha Interna",
            )

            vuetify.VDivider(classes="mt-5")

            vuetify.VContainer("Planos de corte", classes="text-h6 text-center")

            vuetify.VSlider(
                label="X",
                v_model=("offset_clip_x", 0),
                min=-1.5, max=1.5, step=0.05,
                dense=True, hide_details=True,
            )

            vuetify.VCheckbox(
                v_model=("invert_clip_x", False),
                on_icon="mdi-cube-outline",
                off_icon="mdi-cube-off-outline",
                classes="mx-1",
                hide_details=True,
                dense=True,
                label="Inverter corte do eixo X",
            )

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height", ):
            gerar_view()
            view = vtk_widgets.VtkLocalView(renderWindow)
            ctrl.view_update = view.update

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    state.progresso = 0
    state.monitorar_progresso = False
    state.remover_task = False

    server.start()