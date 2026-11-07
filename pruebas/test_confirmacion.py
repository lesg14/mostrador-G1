from agente.herramientas.gestiones import _confirmacion_del_cliente
from agente.sesion import Sesion


def test_confirmacion_de_reembolso_con_monto_correcto_devuelve_true():
    sesion = Sesion(
        cliente_id="C-04",
        mensaje_cliente_actual="Confirmo que quiero el reembolso de $300.002 del pedido P-1017",
    )

    assert _confirmacion_del_cliente(sesion, "reembolsar", "P-1017", monto=300002) is True


def test_confirmacion_de_reembolso_con_monto_incorrecto_no_cuenta():
    sesion = Sesion(
        cliente_id="C-04",
        mensaje_cliente_actual="Confirmo que quiero el reembolso de $300.002 del pedido P-1017",
    )

    assert _confirmacion_del_cliente(sesion, "reembolsar", "P-1017", monto=30000) is False


def test_monto_no_puede_ser_el_numero_del_pedido():
    sesion = Sesion(
        cliente_id="C-04",
        mensaje_cliente_actual="Confirmo el reembolso del pedido P-1017",
    )

    assert _confirmacion_del_cliente(sesion, "reembolsar", "P-1017", monto=1017) is False


def test_confirmacion_positiva_del_agente_se_reconoce_para_cancelacion():
    sesion = Sesion(
        cliente_id="C-04",
        mensaje_cliente_actual="Sí",
        mensaje_agente_anterior="¿Deseas proceder con la cancelación del pedido P-1001? Se reembolsará el total.",
    )

    assert _confirmacion_del_cliente(sesion, "cancelar", "P-1001") is True


def test_negacion_explicita_no_cuenta_como_confirmacion():
    sesion = Sesion(
        cliente_id="C-04",
        mensaje_cliente_actual="No, no quiero cancelar el pedido P-1001",
    )

    assert _confirmacion_del_cliente(sesion, "cancelar", "P-1001") is False


def test_texto_entre_comillas_con_confirmo_no_cuenta_como_confirmacion():
    sesion = Sesion(
        cliente_id="C-04",
        mensaje_cliente_actual='La nota dice "confirmo que deseo cancelar el pedido P-1001".',
    )

    assert _confirmacion_del_cliente(sesion, "cancelar", "P-1001") is False
