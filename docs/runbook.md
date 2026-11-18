# Runbook operativo: pipeline El Índice del Taco

Qué hacer cuando llega una alerta del orquestador (`indice-del-taco-dev-orquestador`), de CloudWatch o de Amazon SNS. Todo está en la región `us-east-2`; los nombres son los de la plantilla `infra/07`.

| Qué llega | Sección |
| :---- | :---- |
| Correo `[Indice del Taco] FALLA en ingesta` | 1 |
| Correo `[Indice del Taco] FALLA en silver` | 2 |
| Correo `[Indice del Taco] FALLA en gold` | 3 |
| Correo `[Indice del Taco] Datos sospechosos o atrasados` | 4 |
| Alarma `indice-del-taco-dev-orquestador-errores` | 5 |
| Alarma `indice-del-taco-dev-sin-ejecucion-7-dias` | 6 |

**Primer paso siempre:** ver qué quedó registrado de la corrida (Athena, base `indice_taco_dev`, workgroup `indice-del-taco-dev`):

```sql
SELECT fecha_hora_inicio, etapa, fuente, estado, registros_leidos, aceptados, rechazados, detalle
FROM registro_ejecuciones
ORDER BY fecha_hora_inicio DESC, etapa
LIMIT 20;
```

Los logs de cada etapa están en CloudWatch: `/aws/lambda/indice-del-taco-dev-ingesta-banxico`, `-silver`, `-gold` y `-orquestador`.

Reprocesar es seguro: todas las etapas son idempotentes (ADR 0017), no se duplican datos.

---

## 1. Falla en la etapa `ingesta` (Banxico)

* **Síntoma:** correo `FALLA en ingesta`, o `estado = 'error'` en `registro_ejecuciones` con etapa `ingesta`.
* **Causas probables:**
  1. Banxico no responde o respondió HTTP 400 (por ejemplo, se excedió el límite de consultas).
  2. El token está mal o no existe en Parameter Store (`/indice-del-taco/dev/banxico_token`).
  3. La respuesta no trae la serie esperada (el mensaje dice "Respuesta inesperada de Banxico").
* **Diagnóstico:** leer el `detalle` del registro y el log `/aws/lambda/indice-del-taco-dev-ingesta-banxico`. Comprobar que el parámetro existe:
  ```bash
  aws ssm get-parameter --name /indice-del-taco/dev/banxico_token --region us-east-2 --query Parameter.LastModifiedDate
  ```
* **Recuperación:** si fue una caída temporal, relanzar el orquestador:
  ```bash
  aws lambda invoke --function-name indice-del-taco-dev-orquestador \
    --payload '{"fecha_ingesta":"AAAA-MM-DD"}' --cli-binary-format raw-in-base64-out out.json
  ```
  Si el token expiró o es incorrecto, actualizar el `SecureString` con `aws ssm put-parameter --overwrite` y relanzar.
* **Nota:** PROFECO **no** forma parte de la corrida automática (la descarga está bloqueada; se carga a mano, ADR 0011).

## 2. Falla en la etapa `silver`

* **Síntoma:** correo `FALLA en silver`.
* **Causas probables:**
  1. **Falta un archivo en bronze:** el detalle dice `No hay archivos en raw/chat/ con fecha_ingesta <= ...` (o `raw/banxico/SP1/`, `raw/interno/`). Nunca se ha subido el chat o la receta.
  2. **Esquema inesperado** (`EsquemaInesperado`): el JSON de Banxico o el CSV de la receta no tienen la forma esperada.
* **Diagnóstico:** `detalle` en `registro_ejecuciones` y el log de `-silver`. Revisar qué hay en bronze:
  ```bash
  aws s3 ls s3://indice-del-taco-dev-bronze-<ID-DE-CUENTA>/raw/ --recursive | tail
  ```
* **Recuperación:** subir el archivo que falta (`raw/chat/fecha_ingesta=AAAA-MM-DD/chat_proveedor.txt` o `raw/interno/fecha_ingesta=AAAA-MM-DD/receta.csv`) y relanzar el orquestador. Si el esquema cambió, corregir el archivo o ajustar el código y desplegar de nuevo.

## 3. Falla en la etapa `gold`

* **Síntoma:** correo `FALLA en gold`. Los datos de gold **no se actualizaron** y el dashboard sigue mostrando la corrida anterior.
* **Causa probable:** `No hay datos en silver_precio_proveedor/silver_receta` (silver no corrió) o un error al calcular.
* **Recuperación:** ver el log de `-gold`. Si silver sí corrió bien, relanzar solo gold:
  ```bash
  aws lambda invoke --function-name indice-del-taco-dev-gold --payload '{}' --cli-binary-format raw-in-base64-out out.json
  ```

## 4. Datos sospechosos o atrasados (la corrida terminó)

* **Síntoma:** correo `Datos sospechosos o atrasados`; la corrida **sí terminó** y gold se actualizó.
* **Causas probables:**
  1. **Cuarentena alta:** más de 10 % de los registros de una fuente se rechazaron (por ejemplo, el proveedor cambió su forma de escribir, un `$0` o una unidad como "caja").
  2. **Fuente atrasada:** el chat o Banxico llevan más de 10 días sin datos nuevos (ADR 0014).
* **Diagnóstico:** ver qué se rechazó y por qué:
  ```sql
  SELECT fuente, regla, motivo, registro_original, linea FROM cuarentena ORDER BY fecha_ingesta DESC, linea;
  ```
* **Recuperación:**
  1. Si hubo registros mal capturados, subir una versión corregida del archivo a bronze **con la misma `fecha_ingesta`** y relanzar `silver` y `gold` (silver reemplaza las particiones y limpia la cuarentena anterior):
     ```bash
     aws lambda invoke --function-name indice-del-taco-dev-silver --payload '{"fecha_ingesta":"AAAA-MM-DD"}' --cli-binary-format raw-in-base64-out out.json
     aws lambda invoke --function-name indice-del-taco-dev-gold --payload '{}' --cli-binary-format raw-in-base64-out out.json
     ```
  2. Si el chat está atrasado, pedir la exportación reciente del proveedor y subirla a `raw/chat/fecha_ingesta=AAAA-MM-DD/chat_proveedor.txt`. Mientras tanto gold sigue usando el último precio vigente.

## 5. Alarma `indice-del-taco-dev-orquestador-errores`

* **Síntoma:** alarma en `ALARM` (puede llegar como segundo correo tras una falla). Significa que la función orquestadora **terminó con error**.
* **Causas probables:** una etapa falló (ver 1 a 3), o el orquestador mismo falló (tiempo agotado de 300 s, memoria, error no controlado).
* **Diagnóstico:** log de `/aws/lambda/indice-del-taco-dev-orquestador`. Si el mensaje es de una etapa, seguir la sección correspondiente.
* **Recuperación:** corregir la causa y relanzar el orquestador. La alarma vuelve a `OK` sola.

## 6. Alarma `indice-del-taco-dev-sin-ejecucion-7-dias`

* **Síntoma:** alarma en `ALARM`: el orquestador **no se ejecutó en 7 días**.
* **Causa probable:** el schedule semanal (`indice-del-taco-dev-semanal`, lunes 6:00 hora de CDMX) está deshabilitado o falla al invocar.
* **Recuperación:**
  1. En la consola, **EventBridge → Scheduler → Schedules**, comprobar que esté en `Enabled`.
  2. Ejecutar a mano el orquestador para poner al día el corte semanal.

---

## 7. Prueba de la falla simulada (verificación de N5)

Para comprobar que las alertas llegan, antes de una entrega o de un cambio mayor:

```bash
aws lambda invoke --function-name indice-del-taco-dev-orquestador \
  --payload '{"simular_falla":"silver"}' --cli-binary-format raw-in-base64-out out.json
```

Qué debe pasar:

1. La invocación termina con error (`FunctionError`): es lo esperado.
2. Llega el correo `[Indice del Taco] FALLA en silver` con la nota "SIMULACION a proposito"; puede llegar un segundo correo de la alarma `orquestador-errores`.
3. En `registro_ejecuciones` queda una fila con etapa `silver` y `estado = 'error'`.
4. Gold **no** se actualiza (la corrida se detiene en la etapa que falla).

Se acepta una falla simulada en `ingesta`, `silver` o `gold`. Después de la prueba, relanzar el orquestador sin parámetros para dejar los datos al día.

---

## 8. Agregar o cambiar una serie de Banxico

Hoy se traen tres series: `SP1` (INPC general, **obligatoria**), `SP66540` (Alimentos, Bebidas y Tabaco) y `SP56386` (Pecuarios).

1. **Buscar la clave** con el catálogo del SIE (no necesita token), por ejemplo:
   ```bash
   curl -G -H "Accept: application/json" --data-urlencode "q=texto a buscar" https://www.banxico.org.mx/SieAPIRest/service/v1/cat/series
   ```
   y comprobarla con `.../series/SPxxxxx` (ver `docs/fuentes.md`).
2. **Traerla a bronze:** agregarla al parámetro `BanxicoSeries` del stack `indice-taco-banxico` (lista separada por comas) y actualizar el stack. Silver descubre solo las series que haya en bronze.
3. **Usarla en gold:** si debe salir en un indicador nuevo, hay que agregar una columna en `gold.py`, en `infra/06` y en el diccionario de datos (hoy las constantes son `SERIE_GENERAL`, `SERIE_ALIMENTOS` y `SERIE_PECUARIOS`).

**Dos cosas que no son error:** los meses que Banxico marca `N/E` («no existe») se omiten sin ir a cuarentena (en estas series son los de 1969 a 1981), y una serie opcional sin archivos
simplemente no aparece (su columna en gold queda vacía). Solo `SP1` es obligatoria: sin ella la etapa `silver` falla.
