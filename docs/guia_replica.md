# Guía de Réplica para Otro Negocio o Sucursal

Esta guía documenta cómo adaptar la solución **El Índice del Taco** a otra taquería, sucursal o pequeño comercio gastronómico sin modificar el código base del pipeline.

---

## 1. Requisitos previos
* Una cuenta de AWS con permisos para desplegar plantillas de **CloudFormation**, **S3**, **Lambda**, **Glue**, **Athena**, **EventBridge**, **SNS** y **SSM Parameter Store**.
* Token gratuito de la API SIE de Banxico para la serie del INPC (`SP1`).
* Exportación periódica en texto plano (`.txt`) del chat con el proveedor de insumos.

---

## 2. Parámetros adaptables por negocio

Para replicar el pipeline en una nueva sucursal o giro comercial, únicamente se ajustan tres elementos de configuración:

1. **Nombre del proyecto y entorno (CloudFormation):**
   Desplegar los stacks `infra/00` a `infra/07` cambiando el parámetro `ProjectName` (ej. `indice-taco-sucursal-norte`):
   ```bash
   P="ProjectName=indice-taco-sucursal-norte Environment=prod"
   