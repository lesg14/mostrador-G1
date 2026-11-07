import json

from agente import herramientas  # noqa: F401
from agente.herramientas.registro import ejecutar
from agente.sesion import Sesion
from tienda import repositorio


def _ejecutar(nombre, argumentos, cliente="C-01", mensaje="", mensaje_anterior=""):
    sesion = Sesion(
        cliente_id=cliente,
        mensaje_cliente_actual=mensaje,
        mensaje_agente_anterior=mensaje_anterior,
    )
    return ejecutar(nombre, json.dumps(argumentos), sesion)


def test_consultar_pedido_solo_entrega_datos_de_la_cuenta():
    resultado = _ejecutar("consultar_pedido", {"numero_pedido": "P-1001"})

    assert resultado["estado"] == "pagado"
    assert resultado["total"] == 180000
    assert "nota_cliente" not in resultado


def test_consultar_pedido_de_otro_cliente_no_revela_datos():
    resultado = _ejecutar("consultar_pedido", {"numero_pedido": "P-1007"})

    assert "error" in resultado
    assert "Televisor" not in str(resultado)


def test_registrar_reclamo_guarda_motivo_y_estado():
    resultado = _ejecutar(
        "registrar_reclamo",
        {
            "numero_pedido": "P-1002",
            "motivo": "Los audífonos no encienden.",
        },
    )

    assert resultado["estado"] == "abierto"
    reclamo = next(r for r in repositorio.leer_reclamos() if r.id == resultado["id"])
    assert reclamo.motivo == "Los audífonos no encienden."


def test_reclamo_abierto_existente_no_se_duplica():
    resultado = _ejecutar(
        "registrar_reclamo",
        {"numero_pedido": "P-1007", "motivo": "Sigue dañado."},
        cliente="C-03",
    )

    assert resultado["reclamo_existente"] is True
    assert resultado["id"] == "R-001"
    assert len([r for r in repositorio.leer_reclamos() if r.numero_pedido == "P-1007"]) == 1


def test_reclamo_preferente_acepta_hasta_el_ultimo_dia_del_plazo():
    resultado = _ejecutar(
        "registrar_reclamo",
        {"numero_pedido": "P-1016", "motivo": "Las flores llegaron marchitas."},
        cliente="C-02",
    )

    assert resultado["fecha_limite"] == "2026-11-02"
    assert resultado["estado"] == "abierto"


def test_cancelar_pedido_exige_confirmacion_y_crea_reembolso_automatico():
    sin_confirmar = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1001", "confirmacion_explicita": False},
    )
    assert "error" in sin_confirmar
    assert next(p for p in repositorio.leer_pedidos() if p.numero == "P-1001").estado == "pagado"
    assert repositorio.leer_reembolsos() == []

    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1001", "confirmacion_explicita": True},
        mensaje="Confirmo explícitamente que deseo cancelar el pedido P-1001.",
    )

    assert resultado["cancelado"] is True
    assert resultado["reembolso"]["monto"] == 180000
    assert resultado["reembolso"]["estado"] == "aprobado"
    assert next(p for p in repositorio.leer_pedidos() if p.numero == "P-1001").estado == "cancelado"


def test_confirmacion_modelada_no_basta_sin_confirmacion_del_cliente():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1001", "confirmacion_explicita": True},
    )

    assert "error" in resultado
    assert next(p for p in repositorio.leer_pedidos() if p.numero == "P-1001").estado == "pagado"


def test_texto_citado_no_cuenta_como_confirmacion():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1001", "confirmacion_explicita": True},
        mensaje='La nota dice "confirmo que deseo cancelar".',
    )

    assert "error" in resultado
    assert next(p for p in repositorio.leer_pedidos() if p.numero == "P-1001").estado == "pagado"


def test_respuesta_afirmativa_confirma_solo_si_el_agente_lo_pidio_para_ese_pedido():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1001", "confirmacion_explicita": True},
        mensaje="Sí.",
        mensaje_anterior="¿Confirmas que quieres cancelar el pedido P-1001?",
    )

    assert resultado["cancelado"] is True


def test_pedido_enviado_no_se_puede_cancelar():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1015", "confirmacion_explicita": True},
        mensaje="Confirmo explícitamente que deseo cancelar el pedido P-1015.",
    )

    assert "error" in resultado
    assert next(p for p in repositorio.leer_pedidos() if p.numero == "P-1015").estado == "enviado"


def test_pedido_en_preparacion_del_dia_actual_se_puede_cancelar():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1005", "confirmacion_explicita": True},
        cliente="C-02",
        mensaje="Confirmo que deseo cancelar el pedido P-1005.",
    )

    assert resultado["cancelado"] is True
    assert resultado["reembolso"]["monto"] == 420000
    assert resultado["reembolso"]["estado"] == "solicitado"
    assert resultado["requiere_asesor"] is True


def test_cancelacion_de_pedido_sobre_el_tope_no_aprueba_el_reembolso_y_escala():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1013", "confirmacion_explicita": True},
        cliente="C-05",
        mensaje="Confirmo que deseo cancelar el pedido P-1013.",
    )

    assert resultado["cancelado"] is True
    assert resultado["reembolso"]["monto"] == 2300000
    assert resultado["reembolso"]["estado"] == "solicitado"
    assert repositorio.leer_reembolsos()[0].estado == "solicitado"
    assert repositorio.leer_escalamientos()[0].numero_pedido == "P-1013"
    assert resultado["escalamiento_id"] == repositorio.leer_escalamientos()[0].id
    assert resultado["requiere_asesor"] is True


def test_cancelacion_dentro_del_tope_no_crea_escalamiento():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1001", "confirmacion_explicita": True},
        mensaje="Confirmo explícitamente que deseo cancelar el pedido P-1001.",
    )

    assert resultado["reembolso"]["estado"] == "aprobado"
    assert repositorio.leer_escalamientos() == []


def test_pedido_en_preparacion_con_plazo_vencido_no_cambia():
    resultado = _ejecutar(
        "cancelar_pedido",
        {"numero_pedido": "P-1009", "confirmacion_explicita": True},
        cliente="C-03",
        mensaje="Confirmo que deseo cancelar el pedido P-1009.",
    )

    assert "error" in resultado
    assert next(p for p in repositorio.leer_pedidos() if p.numero == "P-1009").estado == "en_preparacion"


def test_reembolso_no_procede_sin_cancelacion_ni_reclamo_abierto():
    resultado = _ejecutar(
        "solicitar_reembolso",
        {
            "numero_pedido": "P-1011",
            "monto": 70000,
            "motivo": "No lo necesito.",
            "confirmacion_explicita": True,
        },
        cliente="C-04",
        mensaje="Confirmo el reembolso de $70.000 del pedido P-1011.",
    )

    assert "error" in resultado
    assert repositorio.leer_reembolsos() == []


def test_reembolso_superior_al_limite_se_registra_pendiente_y_se_escala():
    resultado = _ejecutar(
        "solicitar_reembolso",
        {
            "numero_pedido": "P-1017",
            "monto": 300001,
            "motivo": "Solicitado por el cliente.",
            "confirmacion_explicita": True,
        },
        cliente="C-04",
        mensaje="Confirmo el reembolso de $300.001 del pedido P-1017.",
    )

    assert resultado["estado"] == "solicitado"
    assert resultado["requiere_asesor"] is True
    assert repositorio.leer_reembolsos()[0].estado == "solicitado"
    assert repositorio.leer_escalamientos()[0].numero_pedido == "P-1017"


def test_reembolso_no_puede_superar_el_total_pagado():
    resultado = _ejecutar(
        "solicitar_reembolso",
        {
            "numero_pedido": "P-1017",
            "monto": 300002,
            "motivo": "Monto superior al pedido.",
            "confirmacion_explicita": True,
        },
        cliente="C-04",
        mensaje="Confirmo el reembolso de $300.002 del pedido P-1017.",
    )

    assert "error" in resultado
    assert repositorio.leer_reembolsos() == []


def test_reembolsos_parciales_acumulados_no_superan_lo_pagado():
    primero = _ejecutar(
        "solicitar_reembolso",
        {
            "numero_pedido": "P-1017",
            "monto": 200000,
            "confirmacion_explicita": True,
        },
        cliente="C-04",
        mensaje="Confirmo el reembolso de $200.000 del pedido P-1017.",
    )
    segundo = _ejecutar(
        "solicitar_reembolso",
        {
            "numero_pedido": "P-1017",
            "monto": 100002,
            "confirmacion_explicita": True,
        },
        cliente="C-04",
        mensaje="Confirmo el reembolso de $100.002 del pedido P-1017.",
    )

    assert primero["estado"] == "aprobado"
    assert "error" in segundo
    assert sum(r.monto for r in repositorio.leer_reembolsos()) == 200000


def test_escalar_registra_resumen_y_plazo_de_contacto():
    resultado = _ejecutar(
        "escalar_a_persona",
        {"motivo": "Solicitud del cliente", "resumen": "Necesita ayuda con su caso."},
    )

    assert resultado["escalado"] is True
    assert resultado["plazo_contacto"] == "un día hábil como máximo"
    escalamiento = repositorio.leer_escalamientos()[0]
    assert escalamiento.cliente_id == "C-01"
    assert escalamiento.resumen == "Necesita ayuda con su caso."
