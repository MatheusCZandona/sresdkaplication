import json
import logging
import time
from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)


#logs para observabilidade
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("compras-api")

@app.before_request
def marcar_inicio():
    g.inicio = time.perf_counter()

@app.after_request
def registrar_requisicao(resposta):
    duracao_ms = (time.perf_counter() - g.inicio) * 1000

    #para metricas
    rota = request.url_rule.rule if request.url_rule else "desconhecida"
    REQUISICOES.labels(request.method, rota, resposta.status_code).inc()
    DURACAO.labels(request.method, rota).observe(duracao_ms / 1000)


    if resposta.status_code >= 500:
        nivel = logging.ERROR
    elif resposta.status_code >= 400:
        nivel = logging.WARNING
    else:
        nivel = logging.INFO

    logger.log(nivel, json.dumps({
        "evento": "requisicao",
        "metodo": request.method,
        "caminho": request.path,
        "status": resposta.status_code,
        "duracao_ms": round(duracao_ms, 2),
    }))
    return resposta
#lgos até aqui


#metricas com prometheus
REQUISICOES = Counter( #contador do total de requisições
    "http_requisicoes_total",
    "Total de requisições HTTP",
    ["metodo", "rota", "status"],
)
DURACAO = Histogram( #histograma do tempo das requisições
    "http_requisicao_duracao_segundos",
    "Duração das requisições HTTP",
    ["metodo", "rota"],
)
#fim das metricas

COMPRAS = [
    {"id": 1, "item": "teclado", "valor": 150.0},
    {"id": 2, "item": "mouse", "valor": 80.0},
]

@app.get("/")
def home():
    return "Bom dia"

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

@app.get("/v1/compras")
def listar_compras():
    return jsonify(COMPRAS), 200

@app.get("/v1/compras/<int:compra_id>") # busca por id - lsita completa em v1
def buscar_compra(compra_id):
    for compra in COMPRAS:
        if compra["id"] == compra_id:
            return jsonify(compra), 200
    return jsonify(erro="compra não encontrada"), 404


@app.post("/v1/compras") # post em v1
def criar_compra():
    dados = request.get_json(silent=True)

    if not dados or "item" not in dados or "valor" not in dados:
        return jsonify(erro="campos 'item' e 'valor' são obrigatórios"), 400

    nova = {
        "id": max((c["id"] for c in COMPRAS), default=0) + 1,
        "item": dados["item"],
        "valor": dados["valor"],
    }
    COMPRAS.append(nova)
    return jsonify(nova), 200

@app.get("/v1/falha")
def falha_simulada():
    return jsonify(erro="falha simulada para testes"), 500

@app.get("/v2/compras") # faz a listagem por paginação em v2 (versão para testes)
def listar_compras_v2():
    limite = request.args.get("limite", default=10, type=int) # limite de quantos objetos mostrar
    offset = request.args.get("offset", default=0, type=int) #offset a partir de qual objeto mostrar

    if limite < 1 or offset < 0:
        return jsonify(erro="'limite' deve ser >= 1 e 'offset' >= 0"), 400 #bad request por erro do usuario

    pagina = COMPRAS[offset:offset + limite] #exata parte do vetor q se deve mostrar
    return jsonify(
        dados=pagina,
        meta={"total": len(COMPRAS), "limite": limite, "offset": offset},
    ), 200


@app.get("/metrics") #prometheus para metricas
def metricas():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(debug=True, port=5000)