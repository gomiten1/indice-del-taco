# Runbook Operativo — Pipeline El Índice del Taco

Este manual describe los procedimientos de diagnóstico y recuperación ante fallas o alertas emitidas por el orquestador (`indice-del-taco-dev-orquestador`), CloudWatch y Amazon SNS en la región `us-east-2`.

---

## 1. Alerta: Falla en etapa de ingesta (`Banxico` / `PROFECO`)

* **Síntoma:** Correo de SNS con asunto `[ALERTA] Falla en etapa ingesta` o registro en la tabla `registro_ejecuciones` con `estado = 'error'`.
* **Causa probable:**
  1. Indisponibilidad temporal de la API SIE de Banxico o vencimiento/error en el parámetro SSM `/indice-del-taco/dev/banxico_token`.
  2. Bloqueo HTTP `403` en portal externo o ausencia de carga manual quincenal en `bronze`.
* **Diagnóstico:**
  1. Revisar logs en CloudWatch Log Group `/aws/lambda/indice-del-taco-dev-ingesta-banxico`.
  2. Validar existencia del token en Parameter Store:
     ```bash
     aws ssm get-parameter --name /indice-del-taco/dev/banxico_token --region us-east-2
     ```
* **Recuperación:**
  1. Si fue caída temporal de la API, reejecutar manualmente el orquestador (el pipeline es idempotente y no duplica registros):
     ```bash
     aws lambda invoke --function-name indice-del-taco-dev-orquestador \
       --payload '{"fecha_ingesta":"AAAA-MM-DD"}' \
       --cli-binary-format raw-in-base64-out out.json
     ```
  2. Si el token expiró, actualizar el parámetro `SecureString` en SSM y relanzar.

---

## 2. Alerta: Cuarentena alta o datos sospechosos en `Silver`

* **Síntoma:** Alerta de SNS indicando `UMBRAL_CUARENTENA` (> 10 % de registros rechazados) o variación semanal superior al 25 % (`UMBRAL_VARIACION`).
* **Causa probable:** Cambio en el formato de mensajes del proveedor en WhatsApp, errores de dedo en precios (ej. `$0` o unidad inválida) o archivo corrupto en `bronze`.
* **Diagnóstico:**
  1. Consultar los registros rechazados y su motivo en el bucket `cuarentena` (`s3://indice-del-taco-dev-cuarentena-<ID>/fuente=.../`).
  2. Verificar qué línea del archivo crudo en `bronze` detonó el rechazo.
* **Recuperación:**
  1. Corregir o cargar la versión limpia del archivo fuente en `bronze` bajo la misma llave `fecha_ingesta=AAAA-MM-DD/`.
  2. Reejecutar la etapa `silver` y `gold`; Silver sobrescribirá las particiones afectadas y limpiará la cuarentena obsoleta sin duplicar datos:
     ```bash
     aws lambda invoke --function-name indice-del-taco-dev-silver \
       --payload '{"fecha_ingesta":"AAAA-MM-DD"}' \
       --cli-binary-format raw-in-base64-out out.json
     aws lambda invoke --function-name indice-del-taco-dev-gold \
       --payload '{}' \
       --cli-binary-format raw-in-base64-out out.json
     ```

---

## 3. Alerta: Fuente atrasada (`UMBRAL_REZAGO_DIAS > 10`)

* **Síntoma:** Notificación de que el chat del proveedor o Banxico supera 10 días sin datos nuevos.
* **Causa probable:** El proveedor no envió lista de precios en la semana en curso o no se subió el respaldo del chat a `bronze`.
* **Diagnóstico y Acción:**
  1. Confirmar si existe exportación reciente del chat de WhatsApp pendiente de subir a `s3://<bronze>/raw/chat/fecha_ingesta=AAAA-MM-DD/chat_proveedor.txt`.
  2. Mientras no llegue lista nueva, Gold mantiene vigente el último precio válido conocido conforme al contrato de negocio.

---

## 4. Alarma CloudWatch: Orquestador sin ejecuciones en 7 días

* **Síntoma:** Alarma `OrquestadorSinEjecuciones7Dias` en estado `ALARM`.
* **Causa probable:** Deshabilitación accidental de la regla de EventBridge Scheduler (programada cada lunes 6:00 AM CDMX).
* **Recuperación:**
  1. Verificar en la consola de **Amazon EventBridge → Schedules** que la programación esté en estado `Enabled`.
  2. Ejecutar manualmente el orquestador para poner al día el corte semanal.

---

## 5. Prueba de simulación de falla (Verificación N5)

Para validar que las alertas por correo funcionan antes de cada entrega o cambio mayor:
```bash
aws lambda invoke --function-name indice-del-taco-dev-orquestador \
  --payload '{"simular_falla":"silver"}' \
  --cli-binary-format raw-in-base64-out out.json