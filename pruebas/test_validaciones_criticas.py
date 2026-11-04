import json

import pytest

from agente import herramientas  # noqa: F401  (registra las herramientas)
from agente.herramientas.registro import ejecutar
from agente.sesion import Sesion
from tienda import repositorio


def _preparar_datos(tmp_path, monkeypatch, pedido):
    monkeypatch.setattr(repositorio, "DATOS", tmp_path)
    (tmp_path / "clientes.json").write_text(
        json.dumps(
            [
                {
                    "id": "C-01",
                    "nombre": "Cliente de prueba",
                    "correo": "cliente@example.com",
                    "categoria": "regular",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "pedidos.json").write_text(json.dumps([pedido]), encoding="utf-8")


def _pedido_valido(**cambios):
    pedido = {
        "numero": "P-TEST",
        "cliente_id": "C-01",
        "fecha_compra": "2026-11-01",
        "estado": "pagado",
        "productos": [
            {
                "nombre": "Producto de prueba",
                "categoria": "ropa",
                "cantidad": 1,
                "precio_unitario": 10000,
            }
        ],
        "total": 10000,
    }
    return pedido | cambios


@pytest.mark.parametrize(
    ("argumentos", "mensaje"),
    [
        ('{"tema":"fraude"}', "Argumentos inválidos."),
        ("{json incorrecto", "Argumentos inválidos."),
    ],
)
def test_herramienta_rechaza_argumentos_invalidos_antes_de_ejecutarse(
    argumentos, mensaje, monkeypatch
):
    lecturas = []
    monkeypatch.setattr(
        repositorio,
        "leer_politicas",
        lambda: lecturas.append("lectura"),
    )

    resultado = ejecutar("consultar_politica", argumentos, Sesion(cliente_id="C-01"))

    assert resultado["error"] == mensaje
    assert lecturas == []


def test_herramienta_desconocida_se_rechaza_sin_ejecutarse():
    resultado = ejecutar("herramienta_inexistente", "{}", Sesion(cliente_id="C-01"))

    assert "error" in resultado
    assert "No existe la herramienta" in resultado["error"]


@pytest.mark.parametrize(
    ("cambios", "fragmento_error"),
    [
        ({"total": 9999}, "total"),
        ({"estado": "entregado"}, "fecha_entrega"),
        ({"estado": "despachado"}, "estado"),
        ({"campo_inesperado": True}, "campo"),
    ],
)
def test_pedido_invalido_se_rechaza_al_leerlo(
    tmp_path, monkeypatch, cambios, fragmento_error
):
    _preparar_datos(tmp_path, monkeypatch, _pedido_valido(**cambios))

    with pytest.raises(repositorio.ErrorDeDatos, match=fragmento_error):
        repositorio.leer_pedidos()


def test_pedido_de_cliente_inexistente_se_rechaza(tmp_path, monkeypatch):
    _preparar_datos(
        tmp_path,
        monkeypatch,
        _pedido_valido(cliente_id="C-99"),
    )

    with pytest.raises(repositorio.ErrorDeDatos, match="no existe en clientes.json"):
        repositorio.leer_pedidos()


def test_json_malformado_se_rechaza_con_error_de_datos(tmp_path, monkeypatch):
    monkeypatch.setattr(repositorio, "DATOS", tmp_path)
    (tmp_path / "pedidos.json").write_text("[JSON inválido", encoding="utf-8")

    with pytest.raises(repositorio.ErrorDeDatos, match="JSON está mal formado"):
        repositorio.leer_pedidos()
