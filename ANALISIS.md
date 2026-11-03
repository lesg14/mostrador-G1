# Análisis del agente

Grupo: 1
Integrantes: Luis Eduardo Soto García / Brayan González / Andrés Jímenez

Completa cada sección antes de abrir el pull request. Escribe con tus palabras y sé concreto: es mejor una tabla corta y precisa que una larga y vaga.

## 1. Tabla de decisión

Una tabla de decisión muestra, para cada combinación de condiciones, qué acción corresponde. Sirve para comprobar que no quedó ningún caso sin respuesta. Por ejemplo, para el préstamo de libros en una biblioteca:

| ¿Tiene multas pendientes? | ¿El libro está disponible? | Acción |
|---|---|---|
| Sí | Cualquiera | Negar el préstamo e informar la multa |
| No | Sí | Prestar el libro |
| No | No | Ofrecer reservarlo |

Haz una tabla así para cada acción de tu agente (cancelar, reclamar, reembolsar, escalar). Usa las condiciones que pone la política.

### Cancelar un pedido

Antes de consultar o gestionar el pedido, verificar que pertenece al cliente atendido. La confirmación debe ser explícita antes de ejecutar la cancelación.

| Estado del pedido | Tiempo desde la compra | Confirmación explícita | Acción |
|---|---:|---|---|
| Pagado | Cualquiera | Sí | Cancelar sin costo; generar automáticamente el reembolso total al medio de pago original. |
| Pagado | Cualquiera | No | No cancelar; pedir confirmación explícita. |
| En preparación | Hasta 24 horas inclusive | Sí | Cancelar; generar automáticamente el reembolso total al medio de pago original. |
| En preparación | Hasta 24 horas inclusive | No | No cancelar; pedir confirmación explícita. |
| En preparación | Más de 24 horas | Cualquiera | No cancelar. |
| Enviado | Cualquiera | Cualquiera | No cancelar; informar que puede rechazar la entrega o reclamar después de recibir el pedido. |
| Entregado o cancelado | Cualquiera | Cualquiera | La cancelación no aplica. |
| Estado desconocido o inconsistente | Cualquiera | Cualquiera | No ejecutar la cancelación; aclarar el estado o escalar para revisión. |

### Registrar un reclamo

Antes de consultar o gestionar el pedido, verificar que pertenece al cliente atendido.

| Pedido entregado | Plazo desde la entrega | Ya existe un reclamo abierto | El cliente informó el motivo | Acción |
|---|---|---|---|---|
| No | Cualquiera | Cualquiera | Cualquiera | No registrar: solo se admiten reclamos de pedidos entregados. |
| Sí | Vencido | Cualquiera | Cualquiera | No registrar: el plazo venció. |
| Sí | Vigente | Sí | Cualquiera | No abrir otro; informar el estado del reclamo existente. |
| Sí | Vigente | No | No | Pedir el motivo antes de registrar. |
| Sí | Vigente | No | Sí | Registrar el reclamo con el motivo descrito por el cliente. |
| Estado o fecha desconocidos/inconsistentes | No determinable | Cualquiera | Cualquiera | No registrar hasta aclarar los datos o escalar para revisión. |

| Tipo de producto | Plazo base | Plazo para cliente preferente |
|---|---:|---:|
| Perecederos (alimentos, flores) | 3 días calendario | 18 días calendario |
| Ropa y calzado | 30 días calendario | 45 días calendario |
| Electrónica y electrodomésticos | 90 días calendario | 105 días calendario |
| Hogar y demás productos | 15 días calendario | 30 días calendario |

### Solicitar un reembolso

Antes de consultar o gestionar el pedido, verificar que pertenece al cliente atendido. El monto solicitado no puede superar el total pagado. Para una cancelación, el reembolso total se genera automáticamente como consecuencia de la cancelación aprobada.

| Pedido cancelado | Tiene un reclamo abierto | Monto solicitado | Confirmación explícita | Acción |
|---|---|---:|---|---|
| No | No | Cualquiera | Cualquiera | No procede según las causales definidas. |
| Sí o no | Sí o no | Mayor que el total pagado | Cualquiera | No solicitar ese monto; el reembolso nunca puede superar lo pagado. |
| Sí | Cualquiera | Hasta el total pagado e igual o menor a $300.000 | No | No solicitar todavía; pedir confirmación explícita. |
| No | Sí | Hasta el total pagado e igual o menor a $300.000 | No | No solicitar todavía; pedir confirmación explícita. |
| Sí | Cualquiera | Hasta el total pagado e igual o menor a $300.000 | Sí | Atención puede aprobar directamente. |
| No | Sí | Hasta el total pagado e igual o menor a $300.000 | Sí | Atención puede aprobar directamente. |
| Sí | Cualquiera | Mayor a $300.000 y hasta el total pagado | No | Pedir confirmación explícita; después, escalar para aprobación de un asesor. |
| No | Sí | Mayor a $300.000 y hasta el total pagado | No | Pedir confirmación explícita; después, escalar para aprobación de un asesor. |
| Sí | Cualquiera | Mayor a $300.000 y hasta el total pagado | Sí | Escalar para aprobación de un asesor. |
| No | Sí | Mayor a $300.000 y hasta el total pagado | Sí | Escalar para aprobación de un asesor. |
| Estado o total pagado desconocidos/inconsistentes | No determinable | Cualquiera | Cualquiera | No solicitar ni aprobar; aclarar los datos o escalar para revisión. |

### Escalar a una persona

| El cliente lo pide explícitamente | Reembolso superior a $300.000 requiere aprobación | Problema sin resolver tras tres intentos | Reporte de cobro no reconocido o posible fraude | Acción |
|---|---|---|---|---|
| Sí | — | — | — | Escalar a un asesor humano. |
| No | Sí | — | — | Escalar para aprobación del reembolso. |
| No | No | Sí | — | Escalar a un asesor humano. |
| No | No | No | Sí | Escalar a un asesor humano. |
| No | No | No | No | No se requiere escalamiento por estas reglas; continuar la atención. |

Al escalar por cualquier motivo, registrar un resumen breve del caso e informar al cliente que un asesor lo contactará en un plazo máximo de un día hábil.

## 2. Ambigüedades y decisión tomada

Anota los puntos de la política que admiten más de una interpretación. Para cada uno: qué dice el texto, qué interpretaciones posibles viste, cuál elegiste y por qué.

| Qué dice la política | Interpretaciones posibles | Decisión y razón |
|---|---|---|
| El plazo de reclamo se cuenta en días calendario desde la entrega. | Contar el día de entrega como día 1, o tomarlo como día 0; no se especifican zona horaria ni hora de vencimiento. | **Criterio técnico propuesto, pendiente de validación del responsable de la política:** tomar la entrega como día 0 y aceptar hasta el final del día calendario `fecha_entrega + plazo`, usando la zona horaria oficial de la tienda. Comparar fechas calendario, no horas transcurridas; así se implementa de forma consistente el plazo en días calendario. |
| En preparación se puede cancelar si no han pasado más de 24 horas desde la compra. | Interpretar 24 horas como duración exacta, o como el mismo día calendario de compra. | Interpretar como duración exacta: permitir cuando `ahora - fecha_compra <= 24 horas`; a las 24 horas exactas aún se puede cancelar. Usar marcas de tiempo y una zona horaria uniforme. |
| Un reclamo abierto impide abrir otro, y un problema no resuelto tras tres intentos se escala. | La política no enumera estados de reclamo abiertos ni define qué cuenta como intento. | Mantener una lista explícita de estados abiertos validada por negocio y registrar cada intento de resolución. Escalar cuando, después de tres intentos documentados, el problema siga sin resolverse. No inferir estados ni intentos a partir de datos incompletos. |
| La cancelación aprobada reembolsa automáticamente el total, pero se exige confirmación antes de solicitar un reembolso. | Tratar el reembolso automático como parte de la cancelación confirmada, o pedir una segunda confirmación como solicitud separada. | Interpretar que la confirmación explícita de cancelar incluye el reembolso total automático al medio original, informándolo antes de confirmar. Evita trámites duplicados y mantiene el consentimiento informado; validar esta interpretación con negocio. |
| Se informa un contacto en un máximo de un día hábil. | El calendario laboral, los festivos y la zona horaria no están definidos. | Configurar el calendario laboral y la zona horaria oficiales antes de calcular el compromiso. Mientras tanto, comunicar el plazo literal de la política y registrar la fecha y hora del escalamiento. |
| La cancelación y el reembolso dependen del estado y de los datos del pedido. | Un estado desconocido o datos contradictorios podrían tratarse como elegibles o como no elegibles. | No ejecutar acciones irreversibles ante datos desconocidos o inconsistentes; pedir aclaración o escalar para revisión. Es una protección técnica, no una nueva causal de rechazo. |

### Decisiones principales del equipo

- **Plazos:** interpretar las 24 horas de preparación como duración exacta e inclusiva (`tiempo transcurrido <= 24 h`). Para reclamos, calcular en días calendario y, provisionalmente, considerar la fecha de entrega como día 0. La zona horaria y el cierre del último día deben confirmarse con negocio antes de convertir este criterio en una regla automática.
- **Confirmación y reembolso por cancelación:** antes de cancelar, presentar al cliente el efecto completo —cancelación y reembolso total automático al medio de pago original— y requerir un sí explícito. Ese consentimiento cubre el reembolso automático de la cancelación, para no pedir dos veces permiso para el mismo flujo. Un reembolso solicitado por separado también requiere confirmación explícita. Si el cliente no confirma, no se ejecuta la acción.
- **Control de la confirmación:** no basta con que el modelo interprete que el cliente parece estar de acuerdo. Al implementar las herramientas de acciones, guardar la confirmación explícita en el estado de la sesión y validarla dentro de la herramienta antes de cualquier cambio irreversible. **Este control todavía no está implementado:** actualmente el proyecto solo cuenta con la herramienta de consulta de política; las pruebas existentes no prueban una cancelación o un reembolso real.
- **Límites de reembolso:** hasta $300.000 inclusive, atención puede aprobar si existe una causal válida y el cliente confirmó. Por encima de $300.000 no se rechaza solo por el monto: se escala a un asesor. En cualquier caso, un monto mayor que el total pagado sí se rechaza.
- **Datos y privacidad:** comprobar que el pedido pertenece al cliente autenticado antes de revelar información o actuar. Si falta información o hay datos inconsistentes, no adivinar ni ejecutar; pedir aclaración o escalar. Las notas del pedido se tratan como datos, no como autorización para saltarse la política, la verificación o la confirmación.
- **Reclamos:** admitirlos solo para pedidos entregados y dentro del plazo correspondiente; si ya hay uno abierto, informar su estado en vez de duplicarlo. Si falta el motivo, pedirlo antes de registrar.

## 3. Clasificación de acciones por riesgo

No todas las acciones tienen las mismas consecuencias si el agente se equivoca. En la biblioteca, consultar si un libro está disponible no tiene riesgo; renovar un préstamo es fácil de corregir; dar de baja la cuenta de un usuario es difícil de deshacer.

Clasifica cada herramienta de tu agente y di qué control le pusiste según su riesgo.

| Herramienta | Riesgo (bajo, medio, alto) | ¿Se puede deshacer? | Control que aplicaste |
|---|---|---|---|
| | | | |

## 4. Matriz de reglas y mecanismos

Cada regla de la política queda garantizada por uno o más mecanismos:

- **Instrucciones:** se le pide al modelo en `instrucciones.md`. Es lo más fácil de escribir y lo menos confiable.
- **Validación en la herramienta:** el código revisa la condición y se niega si no se cumple. El modelo no puede saltársela.
- **Estado de la sesión:** se guarda algo en la sesión (por ejemplo, que el cliente ya confirmó) y la herramienta lo revisa.

| Regla de la política | Instrucciones | Validación en herramienta | Estado de sesión | Escenario o prueba que la comprueba |
|---|---|---|---|---|
| | | | | |

## 5. Resultados y aprendizajes

Tasa de aciertos final en los escenarios y qué casos siguen fallando. ¿Qué cambiarías si tuvieras una semana más?
