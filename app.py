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

URL_API="http://gerador-old:8080"
LOG_FILE="/deploy/server/logs/log.txt"
LOCAL_TIMEZONE="America/Recife"

def log(mensagem):
    utc_now = datetime.now()
    fuso_horario = pytz.timezone(LOCAL_TIMEZONE)
    timestamp_local = utc_now.replace(tzinfo=pytz.utc).astimezone(fuso_horario)
    timestamp_local_str = timestamp_local.strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a") as file:
        file.write(f"[{timestamp_local_str}] {mensagem}\n")

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

def carregar_vtu(nome_arquivo_malha):
    # Read the source file.
    reader = vtkXMLUnstructuredGridReader()
    reader.SetFileName(nome_arquivo_malha)
    reader.Update()
    output = reader.GetOutput()

    mapper = vtkDataSetMapper()
    mapper.SetInputData(output)
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

    return actor

def gerar_view(lista_arquivos_malhas):
    global malha1, malha2

    malha1 = carregar_vtu(lista_arquivos_malhas[0])
    malha2 = carregar_vtu(lista_arquivos_malhas[1])

    renderer.AddActor(malha1)
    renderer.AddActor(malha2)

    renderer.SetBackground(colors.GetColor3d('Wheat'))
    renderer.ResetCamera()

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

def remover_task_ctrl():
    try:
        state.remover_task = True
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
            'qnt_blocos_zero': qnt_blocos_zero
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
            dir_token = f'/deploy/vtu_files/{token}'

            os.makedirs(dir_token, exist_ok=True)

            nome_arquivo_tar = f'malhas.tar.gz'
            nome_completo_arquivo_tar = f"{dir_token}/{nome_arquivo_tar}"

            with open(nome_completo_arquivo_tar, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            with tarfile.open(nome_completo_arquivo_tar, 'r:gz') as tar:
                tar.extractall(path=dir_token)

            nome_antigo = f'{dir_token}/simplexos_externos.vtu'
            nome_novo = f'/deploy/vtu_files/malha1.vtu'
            os.rename(nome_antigo, nome_novo)

            nome_antigo = f'{dir_token}/simplexos_internos.vtu'
            nome_novo = f'/deploy/vtu_files/malha2.vtu'
            os.rename(nome_antigo, nome_novo)

            log(f"Malhas baixadas com sucesso.")
        else:
            log(f"Erro ao baixar dados do servidor. [Código {response.status_code}: {response.text}]")
    except Exception as error:
        nome_funcao = inspect.currentframe().f_code.co_name
        log(f"Erro nao identificado em {nome_funcao}. [{repr(error)}]")

@state.change("malha1_visivel")
def update_visibilidade_malha1(malha1_visivel, **kwargs):
    malha1.SetVisibility(malha1_visivel)
    ctrl.view_update()

@state.change("malha2_visivel")
def update_visibilidade_malha2(malha2_visivel, **kwargs):
    malha2.SetVisibility(malha2_visivel)
    ctrl.view_update()

@state.change("progresso")
def ativar_btn_regarregar(progresso, **kwargs):
    if(progresso == 100):
        state.desabilitar_recarregar = False
    else:
        state.desabilitar_recarregar = True

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
                    click=remover_task_ctrl, 
                    href="/",
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

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height", ):
            lista_arquivos_malhas = [
                '/deploy/vtu_files/malha1.vtu',
                '/deploy/vtu_files/malha2.vtu'
            ]
            gerar_view(lista_arquivos_malhas)
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