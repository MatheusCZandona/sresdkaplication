import pytest

import app as app_module
from repositorio import RepositorioEmMemoria


@pytest.fixture
def client():
    app_module.repo = RepositorioEmMemoria([
        {"id": 1, "item": "teclado", "valor": 150.0},
        {"id": 2, "item": "mouse", "valor": 80.0},
    ])
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_buscar_compra_existente(client):
    r = client.get("/v1/compras/1")
    assert r.status_code == 200
    assert r.get_json()["item"] == "teclado"


def test_buscar_compra_inexistente(client):
    assert client.get("/v1/compras/99").status_code == 404


def test_criar_compra_valida(client):
    r = client.post("/v1/compras", json={"item": "monitor", "valor": 900})
    assert r.status_code == 201
    assert r.get_json()["id"] == 3


def test_criar_compra_invalida(client):
    r = client.post("/v1/compras", json={"item": "monitor"})
    assert r.status_code == 400


def test_v2_paginacao(client):
    r = client.get("/v2/compras?limite=1&offset=1")
    corpo = r.get_json()
    assert r.status_code == 200
    assert len(corpo["dados"]) == 1
    assert corpo["meta"]["total"] == 2


def test_v2_limite_invalido(client):
    assert client.get("/v2/compras?limite=0").status_code == 400


def test_v1_continua_devolvendo_lista(client):
    assert isinstance(client.get("/v1/compras").get_json(), list)