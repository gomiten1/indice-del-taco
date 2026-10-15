Equipo 2   
**RFP:  El índice del Taco**

**Cliente**: La TaquerIA Opus  
**Contacto**: Doña Ofelia Ruvalcaba, dueña \[[ofeliatumbada123@gmail.com](mailto:ofeliatumbada123@gmail.com)\]

**Equipo redactor**: 

* Arredondo Granados Gerardo — \[rol, ej. líder de proyecto\]   
*  García Ortega Fernanda — \[rol, ej. ingeniería de datos\]  
*  López Estrada Carlos — \[rol, ej. infraestructura y seguridad\]   
* Martínez Jiménez Alejandro — \[rol, ej. calidad de datos\]  
*   Ospino Mérida Emilio Sebastián — \[rol, ej. análisis y dashboard\] 

**Fecha de publicación**: 2026/10/06 

**1\. Quiénes somos**  
Somos La TaquerIA Opus, una taquería tradicional ubicada en la Ciudad de México (Av. Insurgentes Sur \#123, Col. Roma Norte, Cuauhtémoc) especializada en tacos de suadero y pastor. Nuestro equipo consta de 5 personas operativas, atendiendo a decenas de clientes diariamente. Nos dedicamos a vender alimentos de alta calidad, pero actualmente enfrentamos fluctuaciones constantes en los precios de nuestros insumos sin claridad de si corresponden a la realidad del mercado 

**2\. El problema**  
*"Mire, joven, yo lo que quiero saber es si me están viendo la cara. Don Beto me subió como un 30% este año y me dice que es porque todo subió. Y la verdad yo no sé si es cierto. Las otras taqueras de la cuadra me dicen que a ellas no les ha subido tanto, pero a lo mejor compran otra calidad... Con las recetas calculo mis costos, pero ya no me cuadra nada"*.

Actualmente llevamos las cuentas al tanteo y con cuentas en libreta que no nos dan certeza. Hace poco intentamos revisar esto con una ayuda externa, pero el cálculo se rompió y nos quedamos durante dos meses usando números desactualizados sin que nadie se diera cuenta.

Si no resolvemos esto, corremos el riesgo de fijar precios equivocados en la carta, perder dinero en cada taco que vendemos o pagarle de más a nuestros proveedores sin saberlo.

**3\. Qué necesitamos lograr (pasarlo a tabla)**

| \# | Necesidad  | Cómo sabremos que se cumplió (medible)  |
| :---- | :---- | :---- |
| **N1** | Saber cuánto cuesta cada taco (suadero y pastor) cada semana  | Costo por taco en pesos y como índice base 100, disponible antes del lunes 9:00 AM, en al menos 95% de las semanas  |
| **N2** | Saber si el proveedor cobra caro o barato  | Para cada insumo, diferencia en % contra el precio de mayoreo y de menudeo del mercado, actualizada cada semana  |
| **N3** | Saber qué insumo explica el aumento de costos  | Ranking de insumos según cuánto aportaron al cambio del costo en el último trimestre; los 3 principales se muestran con su % de aportación  |
| **N4** | Comparar nuestro costo con la inflación  | Gráfica del Índice del Taco contra la inflación general y la de alimentos de fuentes oficiales, con la misma base 100\.  |
| **N5** | Que nada falle en silencio  | Si la actualización semanal falla o un dato es sospechoso, llega un correo de aviso en menos de 1 hora y queda registrado  |
| **N6** | Poder confiar en los números  | Los datos con errores se apartan y se reportan en lugar de usarse; cualquier semana se puede volver a calcular desde los datos originales con el mismo resultado  |
| **N7** | Entenderlo sin ser experta  | Doña Ofelia responde las 4 preguntas del problema leyendo el tablero, sin ayuda, en menos de 5 minutos (prueba con el cliente)  |
| **N8** | Que otros negocios lo puedan usar.  | Otro negocio de comida puede usar la solución cambiando solo su receta y precios de proveedor, siguiendo una guía escrita  |

**4\. Qué NO queremos en este proyecto**

\- Un sistema de punto de venta, inventarios o facturación.   
\- Predicción de precios futuros o recomendaciones automáticas de precio de venta.   
\- Compras o negociación automática con el proveedor.   
\- Información en tiempo real: una actualización semanal es suficiente.  
\- Otros tacos, otros productos u otras ciudades (solo suadero y pastor en la CDMX).  
\- Una app móvil propia.   
\- Leer automáticamente nuestros chats de WhatsApp. 

**5\. Datos que tenemos y datos que faltan**

| Dato | Formato hoy | Confiabilidad |
| ----- | ----- | ----- |
| Precios del proveedor | Mensajes de WhatsApp, sin formato fijo, con unidades mezcladas (kilo, pieza, paquete) | Baja: hay errores de captura y cambios sin aviso |
| Receta estándar (gramos de carne, tortillas, salsa, etc. por taco) | Anotaciones impresas y de memoria de la dueña | Media: varía según quién cocina |
| Ventas | Registros manuales en libreta y notas de caja.  | Media |

### **Información externa requerida:**

Información pública oficial sobre precios al menudeo en supermercados/tiendas, precios al mayoreo en centrales de abasto e índices oficiales de inflación

**Dudas:**

* ¿Cada fuente se publica cuando dice y siempre en el mismo formato?  
* ¿Los productos públicos corresponden a nuestros insumos? (ej. "suadero" o "carne al pastor" pueden no aparecer tal cual y habrá que usar el corte más parecido).  
* ¿Cómo convertir todas las unidades a una sola (kilo, pieza) sin errores?  
* ¿Qué hacer cuando una fuente se retrasa o trae huecos?

**6\. Restricciones**

* **Presupuesto máximo:** \$900 000 MXN   
* **Plazo de entrega final:** 2026/11/27   
* **Costo de operación mensual máximo:** \$300 MXN en servicios de nube, con alertas de gasto desde el primer día  
* **Seguridad y privacidad:** no pueden quedar expuestos nuestras ventas, el nombre y teléfono del proveedor, sus mensajes ni nuestros precios de compra exactos. El tablero público solo muestra índices y comparaciones. Cada parte del sistema solo debe tener los permisos que necesita.  
* **Quién lo va a usar:** Doña Ofelia, sin conocimientos técnicos; usa principalmente el celular y el correo.  
* **Otras restricciones:**  
  * Debe funcionar en AWS y sin servidores encendidos todo el tiempo. Que no genere costos de infraestructura en desuso   
  * La instalación y configuración de la solución debe estar completamente automatizada y documentada.   
  * Volver a procesar los datos de una misma semana no debe duplicar registros ni alterar los resultados históricos. 

**7\. Qué esperamos recibir**

* **Tablero de control (Dashboard) privado y de acceso seguro:** Una pantalla sencilla e intuitiva diseñada para Doña Ofelia que le responda cuánto cuesta producir cada taco y si su proveedor está cobrando por arriba o por debajo del mercado.   
* **Mecanismo de procesamiento semanal automático:** Un sistema que recolecte, limpie y consolide la información de forma autónoma cada semana, sin requerir que el personal suba archivos manualmente.   
* **Sistema proactivo de alertas:** Notificaciones automáticas por correo electrónico que avisen inmediatamente a los encargados si ocurre una falla en el proceso o si los datos recibidos contienen anomalías graves.   
* **Guía de despliegue y réplica automatizada:** Plantillas y scripts automatizados para instalar, actualizar o recrear todo el sistema en caso de ser necesario.   
* **Documentación de negocio y técnica clara:** Repositorio en GitHub con README, Diccionario de Datos, Registros de Decisiones de Arquitectura (ADRs), Manual de Operación (Runbook) y Reporte de Costos.

**8\. Cómo evaluaremos las propuestas**

| Criterio | Peso (suma 100\) |
| ----- | ----- |
| Responde a nuestras necesidades (N1 a N8) | 30 % |
| Calidad del plan y tiempos | 20 % |
| Manejo de riesgos (fuentes caídas, datos malos, fallas) | 15 % |
| Costo total y costo de operación mensual | 15 % |
| Claridad para un usuario no técnico | 10 % |
| Facilidad para replicarlo en otro negocio | 10 % |

**9\. Qué debe incluir su propuesta**

* SOW con alcance y fuera de alcance explícitos.  
* Calendario con entregas parciales y fechas.  
* Equipo propuesto y rol de cada integrante.  
* Supuestos (ej. disponibilidad de las fuentes públicas, equivalencia de productos).  
* Riesgos identificados y cómo los mitigarán.  
* Precio total y estimación del costo mensual de operación.  
* Cómo demostrarán que se cumple cada necesidad de la sección 3\.

**10\. Calendario del proceso**

* **Fecha límite para preguntas:** 2026/10/10  
* **Fecha límite para entregar propuestas:** 2026/10/16  
* **Fecha de decisión:** 2026/10/20