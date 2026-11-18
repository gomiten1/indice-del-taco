# ADR 0010: Cuenta de AWS, región y acceso del equipo

**Estado:** Aceptada
**Fecha:** 2026-11-16

## Contexto

El SOW supone una cuenta de AWS con usuario raíz con MFA, un usuario IAM por integrante y una región elegida por el equipo. La cuenta real es de la **nueva experiencia de AWS** (inicio de sesión social): AWS administra los permisos humanos, la región es una sola para todos los proyectos y se determina por la dirección de contacto, y no se pueden crear recursos en otra región.

## Decisión

- **Cuenta y región:** se trabaja en la cuenta personal de un integrante, en **`us-east-2`** (la región asignada; no se elige).
- **Plan:** Free Tier con crédito de 120 USD vigente hasta el 2027-05-16. Todos los servicios del proyecto (S3, Lambda, Athena, Glue, EventBridge, SNS, CloudWatch, CloudFormation, Systems Manager, IAM, Budgets) están incluidos en ese plan; no se sube a plan de pago.
- **Acceso:** credenciales temporales con `aws login`, sin access keys de larga duración. Los demás integrantes se invitan como *team members* desde AWS Settings, en vez de crear usuarios IAM. Esto sustituye el "un usuario IAM por integrante" del SOW.
- **Roles de las Lambdas:** siguen siendo IAM con mínimo privilegio, creados por CloudFormation (probado: la cuenta lo permite).
- **Secretos:** tokens en Parameter Store como `SecureString`, nunca en el repo.

## Razón

Es la restricción de la cuenta, no una preferencia. Aceptarla evita pelear con las políticas administradas y mantiene el costo en cero (el gasto esperado es mínimo y el crédito lo cubre).

## Consecuencias

- Las plantillas no fijan región: usan la del perfil, y los nombres de bucket llevan el ID de cuenta.
- Hay que confirmar el límite de gasto en AWS Settings; si se supera, el proyecto se pausa.
- Mientras la cuenta sea personal, el equipo depende de una sola persona para desplegar; la guía de réplica y las plantillas (E6, E8) permiten recrearlo en otra cuenta.
- La región asignada puede no coincidir con la del diagrama ("MX"); el diagrama se actualiza al final.
- **Restricciones del plan gratuito (verificadas el 18/11):** la política de control de servicio del Free Tier niega `iam:*Provider*`, así que **no se pueden crear proveedores de identidad OIDC ni SAML** (ni listarlos). No es posible el despliegue desde GitHub Actions con OIDC; sí están permitidos `codeconnections`, `codebuild` y `codepipeline`. Ver [la documentación de AWS](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html).
