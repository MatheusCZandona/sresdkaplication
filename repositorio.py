from abc import ABC, abstractmethod
import psycopg
from psycopg.rows import dict_row


class RepositorioCompras(ABC):
    @abstractmethod
    def listar(self):
        ...

    @abstractmethod
    def buscar(self, compra_id):
        """Devolve a compra ou None se não existir."""

    @abstractmethod
    def criar(self, item, valor):
        ...


class RepositorioEmMemoria(RepositorioCompras):
    def __init__(self, compras=None):
        self._compras = list(compras) if compras else []

    def listar(self):
        return list(self._compras)

    def buscar(self, compra_id):
        for compra in self._compras:
            if compra["id"] == compra_id:
                return compra
        return None

    def criar(self, item, valor):
        nova = {
            "id": max((c["id"] for c in self._compras), default=0) + 1,
            "item": item,
            "valor": valor,
        }
        self._compras.append(nova)
        return nova

class RepositorioPostgres(RepositorioCompras):
    def __init__(self, url):
        self._url = url

    def _conectar(self):
        return psycopg.connect(self._url, row_factory=dict_row)

    def listar(self):
        with self._conectar() as conn:
            return conn.execute(
                "SELECT id, item, valor FROM compras ORDER BY id"
            ).fetchall()

    def buscar(self, compra_id):
        with self._conectar() as conn:
            return conn.execute(
                "SELECT id, item, valor FROM compras WHERE id = %s",
                (compra_id,),
            ).fetchone()

    def criar(self, item, valor):
        with self._conectar() as conn:
            return conn.execute(
                "INSERT INTO compras (item, valor) VALUES (%s, %s) "
                "RETURNING id, item, valor",
                (item, valor),
            ).fetchone()