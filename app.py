import os
import requests
import json
import tarfile
from datetime import datetime
import pytz
import asyncio

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
    for arquivo_malha in lista_arquivos_malhas:
        actor = carregar_vtu(arquivo_malha)
        renderer.AddActor(actor)

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
            log(f"Erro ao enviar dados ao servidor.")
            log(f"Código {response.status_code}: {response.text}\n")
    except requests.RequestException:
        log("Erro ao consultar o progresso")
    except Exception as error:
        log(f"Erro nao identificado no servidor.")
        log(f"{error}\n")
    
    return 0

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

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
    
        log(f'Progresso: {state.progresso}')

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
            log(f"Dados enviados com sucesso ao servidor.")
            log(f"Resposta do servidor: {response.text}")
            log(f"Token: {state.token}\n")

            state.monitorar_progresso = True
        else:
            log(f"Erro ao enviar dados ao servidor.")
            log(f"Código {response.status_code}: {response.text}\n")
    except Exception as error:
        log(f"Erro ao preparar dados para envio ao servidor.")
        log(f"{error}\n")

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

            log(f"Arquivo baixado com sucesso. ({nome_arquivo_tar})\n")

            with tarfile.open(nome_completo_arquivo_tar, 'r:gz') as tar:
                tar.extractall(path=dir_token)

            log(f"Arquivos extraídos com sucesso.\n")

            nome_antigo = f'{dir_token}/simplexos_externos.vtu'
            nome_novo = f'/deploy/vtu_files/malha1.vtu'
            os.rename(nome_antigo, nome_novo)

            nome_antigo = f'{dir_token}/simplexos_internos.vtu'
            nome_novo = f'/deploy/vtu_files/malha2.vtu'
            os.rename(nome_antigo, nome_novo)

            log(f"Arquivos renomeados.\n")
        else:
            log(f"Erro ao baixar dados do servidor.")
            log(f"Código {response.status_code}: {response.text}\n")
    except Exception as error:
        log(f"Erro ao preparar requisição de download.")
        log(f"{error}\n")


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
            v_model=("nivel_refinamento", 3),
            type="number"
        )
        vuetify.VTextField(
            label="Quantidade de Blocos Nível Zero",
            v_model=("qnt_blocos_zero", 4),
            type="number"
        )

        vuetify.VBtn("Gerar malha", click=submit_form)

        # Barra de progresso
        vuetify.VProgressLinear(
            v_model=("progresso", 0),  # Barra de progresso vinculada ao estado
            color="blue",
            height=20,
            rounded=True
        )

        # ta duplicando a funcao atualizar_progresso a cada reload
        vuetify.VBtn("Recarregar página", href="/")

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height", ):
            lista_arquivos_malhas = [
                '/deploy/vtu_files/malha1.vtu',
                '/deploy/vtu_files/malha2.vtu'
            ]
            gerar_view(lista_arquivos_malhas)
            view = vtk_widgets.VtkLocalView(renderWindow)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    state.progresso = 0
    state.monitorar_progresso = False

    server.start()