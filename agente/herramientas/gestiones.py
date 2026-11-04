"""Herramientas para consultar pedidos y gestionar casos de atención."""
import re
from datetime import timedelta

from pydantic import BaseModel, Field

from agente.herramientas.registro import ErrorDeHerramienta, herramienta
from agente.sesion import Sesion
from tienda import repositorio

LIMITE_APROBACION_DIRECTA = 300_000
PLAZOS_RECLAMO = {
    "perecedero": 3,
    "ropa": 30,
    "electronica": 90,
    "hogar": 15,
}


def _pedido_del_cliente(sesion: Sesion, numero: str) -> repositorio.Pedido:
    _cliente_del_sesion(sesion)

    pedido = next(
        (pedido for pedido in repositorio.leer_pedidos() if pedido.numero == numero),
        None,
    )
    if pedido is None or pedido.cliente_id != sesion.cliente_id:
        raise ErrorDeHerramienta(
            "No encontré ese pedido en la cuenta autenticada o no tienes acceso a él."
        )
    return pedido


def _cliente_del_sesion(sesion: Sesion) -> repositorio.Cliente:
    cliente = next(
        (c for c in repositorio.leer_clientes() if c.id == sesion.cliente_id),
        None,
    )
    if cliente is None:
        raise ErrorDeHerramienta("No pude verificar la cuenta de esta sesión.")
    return cliente


def _sin_comillas(texto: str) -> str:
    return re.sub(r"[«“\"].*?[»”\"]", "", texto, flags=re.S)


def _confirmacion_del_cliente(
    sesion: Sesion,
    accion: str,
    numero_pedido: str,
    monto: int | None = None,
) -> bool:
    texto = _sin_comillas(sesion.mensaje_cliente_actual).casefold()
    if re.search(
        r"\bno\b.{0,30}\b(?:confirmo|autorizo|acepto|quiero|deseo|de acuerdo)\b",
        texto,
    ):
        return False
    confirma = bool(
        re.search(r"\b(?:confirmo|autorizo|acepto|de acuerdo)\b", texto)
        or re.search(
            r"\bs[ií]\b.{0,40}\b(?:confirmo|quiero|deseo|autorizo|adelante|hazlo|cancela|solicito)\b",
            texto,
        )
    )
    accion_en_mensaje = "cancel" in texto if accion == "cancelar" else "reembols" in texto
    referencia_en_mensaje = numero_pedido.casefold() in texto
    monto_en_mensaje = monto is None or str(monto) in re.sub(r"\D", "", texto)
    if confirma and accion_en_mensaje and referencia_en_mensaje and monto_en_mensaje:
        return True

    afirmativa_breve = bool(
        re.match(r"\s*(?:s[ií]|claro|correcto|de acuerdo|confirmado)\b", texto)
    )
    mensaje_anterior = _sin_comillas(sesion.mensaje_agente_anterior).casefold()
    accion_mencionada = (
        "cancel" in mensaje_anterior if accion == "cancelar" else "reembols" in mensaje_anterior
    )
    monto_mencionado = (
        monto is None
        or str(monto) in re.sub(r"\D", "", mensaje_anterior)
    )
    return bool(
        afirmativa_breve
        and re.search(r"confirm", mensaje_anterior)
        and accion_mencionada
        and numero_pedido.casefold() in mensaje_anterior
        and monto_mencionado
    )


def _siguiente_id(prefijo: str, elementos: list) -> str:
    patron = re.compile(rf"^{re.escape(prefijo)}-(\d+)$")
    mayor = max(
        (
            int(coincidencia.group(1))
            for elemento in elementos
            if (coincidencia := patron.fullmatch(elemento.id))
        ),
        default=0,
    )
    return f"{prefijo}-{mayor + 1:03d}"


def _reclamo_abierto(pedido: repositorio.Pedido) -> repositorio.Reclamo | None:
    reclamos = repositorio.leer_reclamos()
    relacionados = [r for r in reclamos if r.numero_pedido == pedido.numero]
    if any(r.cliente_id != pedido.cliente_id for r in relacionados):
        raise ErrorDeHerramienta("Hay datos de reclamo inconsistentes; no puedo continuar.")
    return next((r for r in relacionados if r.estado == "abierto"), None)


def _reembolsos_del_pedido(
    pedido: repositorio.Pedido,
    reembolsos: list[repositorio.Reembolso] | None = None,
) -> list[repositorio.Reembolso]:
    reembolsos = reembolsos if reembolsos is not None else repositorio.leer_reembolsos()
    relacionados = [r for r in reembolsos if r.numero_pedido == pedido.numero]
    if any(r.cliente_id != pedido.cliente_id for r in relacionados):
        raise ErrorDeHerramienta("Hay datos de reembolso inconsistentes; no puedo continuar.")
    return relacionados


def _crear_escalamiento(
    sesion: Sesion,
    motivo: str,
    resumen: str,
    numero_pedido: str | None = None,
) -> repositorio.Escalamiento:
    escalamientos = repositorio.leer_escalamientos()
    escalamiento = repositorio.Escalamiento(
        id=_siguiente_id("E", escalamientos),
        cliente_id=sesion.cliente_id,
        numero_pedido=numero_pedido,
        fecha=repositorio.HOY,
        motivo=motivo,
        resumen=resumen,
    )
    escalamientos.append(escalamiento)
    repositorio.guardar_escalamientos(escalamientos)
    return escalamiento


class ArgsConsultarPedido(BaseModel):
    numero_pedido: str = Field(description="Número del pedido que el cliente identifica como suyo.")


@herramienta
def consultar_pedido(sesion: Sesion, args: ArgsConsultarPedido) -> dict:
    """Consulta el estado y los datos básicos de un pedido propio del cliente autenticado."""
    pedido = _pedido_del_cliente(sesion, args.numero_pedido)
    return {
        "numero": pedido.numero,
        "estado": pedido.estado,
        "fecha_compra": pedido.fecha_compra.isoformat(),
        "fecha_entrega": pedido.fecha_entrega.isoformat() if pedido.fecha_entrega else None,
        "total": pedido.total,
        "productos": [
            {
                "nombre": producto.nombre,
                "categoria": producto.categoria,
                "cantidad": producto.cantidad,
                "precio_unitario": producto.precio_unitario,
            }
            for producto in pedido.productos
        ],
    }


class ArgsRegistrarReclamo(BaseModel):
    numero_pedido: str = Field(description="Número del pedido propio que el cliente recibió.")
    motivo: str = Field(min_length=1, max_length=500, description="Motivo del reclamo descrito por el cliente.")
    producto: str | None = Field(
        default=None,
        description="Nombre del producto afectado; requerido si el pedido contiene varios productos.",
    )


@herramienta
def registrar_reclamo(sesion: Sesion, args: ArgsRegistrarReclamo) -> dict:
    """Registra un reclamo elegible para un pedido entregado, con el motivo del cliente."""
    pedido = _pedido_del_cliente(sesion, args.numero_pedido)
    if pedido.estado != "entregado" or pedido.fecha_entrega is None:
        raise ErrorDeHerramienta("Solo se puede reclamar por un pedido entregado.")
    if pedido.fecha_entrega < pedido.fecha_compra or pedido.fecha_entrega > repositorio.HOY:
        raise ErrorDeHerramienta("La fecha de entrega del pedido es inconsistente; no puedo registrar el reclamo.")

    existente = _reclamo_abierto(pedido)
    if existente:
        return {
            "reclamo_existente": True,
            "id": existente.id,
            "estado": existente.estado,
            "motivo": existente.motivo,
        }

    cliente = next(c for c in repositorio.leer_clientes() if c.id == sesion.cliente_id)
    if args.producto:
        producto = next(
            (p for p in pedido.productos if p.nombre.casefold() == args.producto.strip().casefold()),
            None,
        )
        if producto is None:
            raise ErrorDeHerramienta("El producto indicado no coincide con los productos de ese pedido.")
    elif len(pedido.productos) == 1:
        producto = pedido.productos[0]
    else:
        raise ErrorDeHerramienta(
            "Indica cuál producto del pedido presenta el problema para verificar el plazo correcto."
        )
    dias = PLAZOS_RECLAMO[producto.categoria]
    if cliente.categoria == "preferente":
        dias += 15
    fecha_limite = pedido.fecha_entrega + timedelta(days=dias)
    if repositorio.HOY > fecha_limite:
        raise ErrorDeHerramienta(
            f"El plazo para reclamar venció el {fecha_limite.isoformat()}."
        )

    reclamos = repositorio.leer_reclamos()
    reclamo = repositorio.Reclamo(
        id=_siguiente_id("R", reclamos),
        numero_pedido=pedido.numero,
        cliente_id=sesion.cliente_id,
        fecha=repositorio.HOY,
        motivo=args.motivo.strip(),
        estado="abierto",
    )
    if not reclamo.motivo:
        raise ErrorDeHerramienta("El motivo del reclamo no puede estar vacío.")
    reclamos.append(reclamo)
    repositorio.guardar_reclamos(reclamos)
    return {
        "reclamo_existente": False,
        "id": reclamo.id,
        "numero_pedido": pedido.numero,
        "estado": reclamo.estado,
        "fecha_limite": fecha_limite.isoformat(),
    }


class ArgsCancelarPedido(BaseModel):
    numero_pedido: str = Field(description="Número del pedido propio que se desea cancelar.")
    confirmacion_explicita: bool = Field(
        description="True solo si el cliente confirmó explícitamente que quiere cancelar este pedido."
    )


@herramienta
def cancelar_pedido(sesion: Sesion, args: ArgsCancelarPedido) -> dict:
    """Cancela un pedido elegible con confirmación y genera su reembolso total automático."""
    pedido = _pedido_del_cliente(sesion, args.numero_pedido)
    if pedido.estado == "enviado":
        raise ErrorDeHerramienta(
            "El pedido enviado no se puede cancelar; el cliente puede rechazar la entrega."
        )
    if pedido.estado not in {"pagado", "en_preparacion"}:
        raise ErrorDeHerramienta("La cancelación no aplica a un pedido entregado o ya cancelado.")
    if pedido.estado == "en_preparacion":
        antiguedad = (repositorio.HOY - pedido.fecha_compra).days
        if antiguedad < 0:
            raise ErrorDeHerramienta("La fecha de compra del pedido es posterior a la fecha actual de la tienda.")
        if antiguedad == 1:
            raise ErrorDeHerramienta(
                "No puedo verificar el plazo exacto de 24 horas porque el pedido no registra la hora de compra."
            )
        if antiguedad > 1:
            raise ErrorDeHerramienta("El plazo de 24 horas para cancelar el pedido en preparación venció.")

    if not args.confirmacion_explicita or not _confirmacion_del_cliente(
        sesion, "cancelar", pedido.numero
    ):
        raise ErrorDeHerramienta("Necesito la confirmación explícita del cliente antes de cancelar.")

    pedidos = repositorio.leer_pedidos()
    for existente in pedidos:
        if existente.numero == pedido.numero:
            existente.estado = "cancelado"

    reembolsos = repositorio.leer_reembolsos()
    if _reembolsos_del_pedido(pedido, reembolsos):
        raise ErrorDeHerramienta("El pedido ya tiene un reembolso registrado; requiere revisión.")
    reembolso = repositorio.Reembolso(
        id=_siguiente_id("RE", reembolsos),
        numero_pedido=pedido.numero,
        cliente_id=sesion.cliente_id,
        fecha=repositorio.HOY,
        monto=pedido.total,
        motivo="Reembolso automático por cancelación confirmada",
        estado="aprobado",
    )
    reembolsos.append(reembolso)

    repositorio.guardar_reembolsos(reembolsos)
    repositorio.guardar_pedidos(pedidos)
    return {
        "cancelado": True,
        "numero_pedido": pedido.numero,
        "estado": "cancelado",
        "reembolso": {
            "id": reembolso.id,
            "monto": reembolso.monto,
            "estado": reembolso.estado,
            "medio": "medio de pago original",
        },
    }


class ArgsSolicitarReembolso(BaseModel):
    numero_pedido: str = Field(description="Número del pedido propio cancelado o con reclamo abierto.")
    monto: int = Field(gt=0, description="Monto entero en pesos colombianos que se solicita reembolsar.")
    motivo: str = Field(
        default="Solicitud de reembolso del cliente",
        min_length=1,
        max_length=500,
        description="Motivo breve del reembolso.",
    )
    confirmacion_explicita: bool = Field(
        description="True solo si el cliente confirmó explícitamente el monto que desea solicitar."
    )


@herramienta
def solicitar_reembolso(sesion: Sesion, args: ArgsSolicitarReembolso) -> dict:
    """Solicita un reembolso elegible; los montos altos quedan pendientes de aprobación humana."""
    pedido = _pedido_del_cliente(sesion, args.numero_pedido)
    reclamo = _reclamo_abierto(pedido)
    if pedido.estado != "cancelado" and reclamo is None:
        raise ErrorDeHerramienta(
            "Solo procede un reembolso por un pedido cancelado o con un reclamo abierto."
        )

    reembolsos = repositorio.leer_reembolsos()
    relacionados = _reembolsos_del_pedido(pedido, reembolsos)
    disponible = pedido.total - sum(reembolso.monto for reembolso in relacionados)
    if args.monto > disponible:
        raise ErrorDeHerramienta(
            f"El monto solicitado supera lo disponible del total pagado ({disponible} pesos)."
        )
    if not args.confirmacion_explicita or not _confirmacion_del_cliente(
        sesion, "reembolsar", pedido.numero, args.monto
    ):
        raise ErrorDeHerramienta(
            "Necesito la confirmación explícita del cliente sobre el monto antes de solicitar el reembolso."
        )

    estado = "aprobado" if args.monto <= LIMITE_APROBACION_DIRECTA else "solicitado"
    reembolso = repositorio.Reembolso(
        id=_siguiente_id("RE", reembolsos),
        numero_pedido=pedido.numero,
        cliente_id=sesion.cliente_id,
        fecha=repositorio.HOY,
        monto=args.monto,
        motivo=args.motivo.strip(),
        estado=estado,
    )
    if not reembolso.motivo:
        raise ErrorDeHerramienta("El motivo del reembolso no puede estar vacío.")
    reembolsos.append(reembolso)
    repositorio.guardar_reembolsos(reembolsos)

    resultado = {
        "id": reembolso.id,
        "numero_pedido": pedido.numero,
        "monto": reembolso.monto,
        "estado": reembolso.estado,
    }
    if estado == "solicitado":
        escalamiento = _crear_escalamiento(
            sesion,
            "Aprobación de reembolso superior a $300.000",
            f"Reembolso de {args.monto} pesos solicitado para el pedido {pedido.numero}; "
            "requiere aprobación de un asesor.",
            pedido.numero,
        )
        resultado["escalamiento_id"] = escalamiento.id
        resultado["requiere_asesor"] = True
    return resultado


class ArgsEscalarAPersona(BaseModel):
    motivo: str = Field(min_length=1, max_length=200, description="Razón por la que se escala el caso.")
    resumen: str = Field(min_length=1, max_length=500, description="Resumen breve para el asesor.")
    numero_pedido: str | None = Field(
        default=None,
        description="Número de pedido propio relacionado, si aplica.",
    )


@herramienta
def escalar_a_persona(sesion: Sesion, args: ArgsEscalarAPersona) -> dict:
    """Registra el caso para que un asesor humano continúe la atención."""
    _cliente_del_sesion(sesion)
    if args.numero_pedido:
        _pedido_del_cliente(sesion, args.numero_pedido)
    motivo = args.motivo.strip()
    resumen = args.resumen.strip()
    if not motivo or not resumen:
        raise ErrorDeHerramienta("El motivo y el resumen del escalamiento no pueden estar vacíos.")
    escalamiento = _crear_escalamiento(
        sesion,
        motivo,
        resumen,
        args.numero_pedido,
    )
    return {
        "escalado": True,
        "id": escalamiento.id,
        "plazo_contacto": "un día hábil como máximo",
    }
