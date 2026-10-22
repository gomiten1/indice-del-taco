# Aclaraciones con el cliente

Inconsistencias detectadas en el material de La TaquerIA Opus (RFP, brief del proyecto, sesión de descubrimiento y extracto del chat de Don Beto). Se validan con Doña Ofelia; mientras tanto se documenta el supuesto con el que se trabaja y no se inventa ningún dato.

## Inconsistencias

| # | Qué dice el cliente | Qué muestran los datos | Pregunta para la dueña | Supuesto provisional | Estado |
| :---- | :---- | :---- | :---- | :---- | :---- |
| A1 | Don Beto le subió "como un 30%" este año | En el chat, de enero a septiembre de 2026, el suadero pasó de $165 a $185 (≈12.1%) y el pastor de $138 a $155 (≈12.3%). La longaniza pasó de $110 a $118 (≈7.3%) | ¿El 30% se calcula sobre qué producto, qué periodo y qué precio base? ¿Incluye otros insumos o cargos? | Se usa el precio real del chat; el ≈12% se reporta como dato observado y no se reemplaza por el 30% | Pendiente |
| A2 | De un kilo de suadero salen "como 25 tacos"; de un kilo de pastor, "como quince" | La receta usa 55 g de suadero (1000 / 55 ≈ 18 tacos por kilo) y 50 g de pastor (20 tacos por kilo). Con 25 tacos por kilo serían 40 g por taco; con 15, ≈67 g | ¿Cuál es el peso real de carne por taco en cada tipo? ¿Cuánto varía según quién cocina? | Se usa la receta (55 g y 50 g) para el costo teórico y se muestra una sensibilidad con las otras cifras | Pendiente |
| A3 | "El kilo me sale como en doscientos veinte" (pastor) | El chat muestra el pastor entre $138 y $155 por kilo. Aun repartiendo el sobrante del trompo (≈12% de lo comprado), el costo por kilo vendido sería ≈$176, no $220 | ¿Qué incluye ese precio: solo la carne, el adobo, el flete, otros insumos? | Se usa el precio del chat para la carne; los $220 no entran al cálculo hasta aclararlos | Pendiente |
| A4 | Compra unos 55 kg diarios de pastor y vende unos 400 tacos en un buen día (200 en uno malo) | Con 50 g por taco, 400 tacos usan 20 kg. Restando el sobrante de 6 a 7 kg, los ≈48 kg usados implicarían ≈120 g por taco a 400 tacos, o más de 240 g a 200 tacos | ¿Los 400 tacos incluyen mostrador y apps? ¿El pastor se usa también en otros platillos? ¿Qué parte es merma? | La receta se toma tal cual; el volumen no entra al índice y se reporta como análisis aparte | Pendiente |
| A5 | El sobrante del trompo (6 a 7 kg diarios) es la cena del personal y no se registra | La receta no incluye ese sobrante, que es un costo real de la carne | ¿Debe contarse como costo del taco? ¿Cuánto sobra en promedio y cuánto varía? | El índice base usa la receta sin merma; se reporta también una versión con merma (ADR 0005) | Pendiente |
| A6 | Don Beto manda sus precios "el lunes en la noche" | En el extracto del chat, los 8 mensajes de Don Beto son en jueves, entre las 6:48 y las 7:15 de la mañana | ¿Cuándo llegan realmente los precios? ¿Hay un día fijo? | Corte semanal el domingo a las 23:59 con el último precio vigente, para tener el costo disponible el lunes a las 9:00 (N1) | Pendiente |

## Preguntas pendientes

Datos que necesitaríamos y que la dueña no ha dado. Hasta que lleguen, se marcan como "sin dato" o se estiman con precios públicos, sin inventarlos:

1. ¿A qué precio compra la tortilla (La Reyna) y los insumos de la Central de Abasto (cebolla, cilantro, limón, piña, chiles)?
2. ¿Don Beto surte también el suadero y la longaniza, o solo el pastor? ¿Hay otros proveedores de carne?
3. ¿La salsa verde y la roja se preparan en el local o se compran? ¿Cuál es su costo por taco?
4. ¿Qué parte de los $600,000 mensuales de ventas son tacos de pastor y suadero?
5. ¿Desde qué fecha quiere comparar los costos (semana base del índice)?
6. ¿Quién puede entregar los exportes de ventas del sistema del mostrador (Diego, la cajera) y con qué frecuencia?

## Cómo se actualiza este archivo

- Cada aclaración se registra con fecha, respuesta del cliente y quién la validó.
- Cuando se resuelve, se actualiza el supuesto en el cálculo y se anota el cambio en el ADR o en el diccionario de datos que corresponda.