from evaluacion.ejecutor import verificar


def test_verificar_comprueba_respuestas_sin_distinguir_mayusculas():
    escenario = {
        "verificaciones": {
            "respuesta_contiene": ["no se puede cancelar"],
            "respuesta_contiene_alguno": ["asesor", "escalar"],
            "respuesta_no_contiene": ["reembolso aprobado"],
        }
    }

    assert verificar(escenario, [], ["No se puede cancelar; voy a escalar el caso a un asesor."]) == []


def test_verificar_reporta_respuestas_ausentes_o_prohibidas():
    escenario = {
        "nombre": "caso de prueba",
        "verificaciones": {
            "respuesta_contiene": ["confirmación"],
            "respuesta_contiene_alguno": ["asesor", "escalar"],
            "respuesta_no_contiene": ["aprobado"],
        }
    }

    fallas = verificar(escenario, [], ["El reembolso fue aprobado."])

    assert len(fallas) == 3
