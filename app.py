import json
import logging
import time
from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import os
import redis
from repositorio import RepositorioComCache, RepositorioEmMemoria, RepositorioPostgres

INSTANCIA = os.environ.get("INSTANCIA", "local")

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

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
    
    resposta.headers["X-Instancia"] = INSTANCIA
    
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

if DATABASE_URL:
    repo = RepositorioPostgres(DATABASE_URL)
else:
    repo = RepositorioEmMemoria([
        {"id": 1, "item": "teclado", "valor": 150.0},
        {"id": 2, "item": "mouse", "valor": 80.0},
    ])

REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL:
    cliente_redis = redis.Redis.from_url(
        REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5
    )
    repo = RepositorioComCache(repo, cliente_redis, ttl_segundos=30)

@app.get("/")
def home():
    return "Bom dia"

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

@app.get("/v1/compras")
def listar_compras():
    return jsonify(repo.listar()), 200


@app.get("/v1/compras/<int:compra_id>")
def buscar_compra(compra_id):
    compra = repo.buscar(compra_id)
    if compra is None:
        return jsonify(erro="compra não encontrada"), 404
    return jsonify(compra), 200


@app.post("/v1/compras")
def criar_compra():
    dados = request.get_json(silent=True)

    if not dados or "item" not in dados or "valor" not in dados:
        return jsonify(erro="campos 'item' e 'valor' são obrigatórios"), 400

    nova = repo.criar(dados["item"], dados["valor"])
    return jsonify(nova), 201



@app.get("/v1/falha")
def falha_simulada():
    return jsonify(erro="falha simulada para testes"), 500

@app.get("/v2/compras")
def listar_compras_v2():
    limite = request.args.get("limite", default=10, type=int)
    offset = request.args.get("offset", default=0, type=int)

    if limite < 1 or offset < 0:
        return jsonify(erro="'limite' deve ser >= 1 e 'offset' >= 0"), 400

    compras = repo.listar()
    pagina = compras[offset:offset + limite]
    return jsonify(
        dados=pagina,
        meta={"total": len(compras), "limite": limite, "offset": offset},
    ), 200

@app.get("/metrics") #prometheus para metricas
def metricas():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(debug=True, port=5000)