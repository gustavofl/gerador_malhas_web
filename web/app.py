from flask import Flask, jsonify, request
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify

# Inicializar Flask
app = Flask(__name__)

# Definir uma rota Flask simples
@app.route('/api/data', methods=['GET'])
def get_data():
    data = request.json
    return jsonify(data)

# Inicializar Trame
server = get_server(client_type = "vue2")

# Definir a interface Trame
with SinglePageLayout(server) as layout:
    layout.title.set_text("Trame e Flask Juntos")
    
    with layout.content:
        vuetify.VBtn("Clique aqui", click="alert('Olá do Trame')")

# Integrar Flask com Trame
@app.route("/trame")
def trame_app():
    return server.get_root_url()

# Iniciar o servidor Flask
if __name__ == "__main__":
    server.start(
        app=app,  # Integrar Flask com Trame
        on_ready=lambda: print("Servidor Trame e Flask rodando..."),
        port=8080,  # Pode definir uma porta diferente
    )
