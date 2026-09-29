"""
Aplicação Flask para Buzzmonitor Automático
Hospedável em Replit ou qualquer servidor Python
"""

from flask import Flask, render_template, jsonify, request
from threading import Thread
import os
from pathlib import Path
from src.reply_from_sheet import main as run_script

app = Flask(__name__)

# Estado da execução
execution_state = {
    "running": False,
    "status": "Aguardando",
    "error": None,
}


@app.route("/")
def index():
    """Página principal"""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Retorna status da execução"""
    return jsonify(execution_state)


@app.route("/api/run", methods=["POST"])
def run_execution():
    """Inicia a execução do script"""
    global execution_state

    if execution_state["running"]:
        return jsonify({"error": "Script já está em execução"}), 400

    execution_state["running"] = True
    execution_state["status"] = "Iniciando..."
    execution_state["error"] = None

    # Rodar em thread separada para não bloquear
    thread = Thread(target=_run_script_thread)
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Script iniciado"})


def _run_script_thread():
    """Executa o script em uma thread separada"""
    global execution_state
    try:
        execution_state["status"] = "Rodando..."
        run_script()
        execution_state["status"] = "✓ Concluído com sucesso!"
    except Exception as e:
        execution_state["status"] = "❌ Erro"
        execution_state["error"] = str(e)
    finally:
        execution_state["running"] = False


@app.route("/api/config", methods=["GET"])
def get_config():
    """Retorna informações de configuração (para debug)"""
    env_file = Path(".env")
    config_ok = env_file.exists()

    credentials_file = Path("credentials/service_account.json")
    credentials_ok = credentials_file.exists()

    return jsonify(
        {
            "env_configured": config_ok,
            "credentials_configured": credentials_ok,
            "ready": config_ok and credentials_ok,
        }
    )


if __name__ == "__main__":
    # Verificar se arquivos necessários existem
    if not Path(".env").exists():
        print("⚠️  AVISO: Arquivo .env não encontrado!")
        print("   Copie .env.example para .env e configure as variáveis")

    if not Path("credentials/service_account.json").exists():
        print("⚠️  AVISO: Arquivo credentials/service_account.json não encontrado!")
        print("   Coloque o arquivo JSON da conta de serviço do Google")

    # Rodar Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
