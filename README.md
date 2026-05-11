# Security Platform — jgutierrezdtt

> **Repositorio central de seguridad** para la organización `jgutierrezdtt`.  
> Proporciona workflows reutilizables, reglas Semgrep, tutoriales y el template base para cualquier repositorio nuevo.

---

## Indice de tutoriales

| Tutorial | Descripcion |
|----------|-------------|
| [Mi PR esta bloqueado — que hago](docs/tutorials/pr-blocked-guide.md) | Guia rapida para developers: leer el reporte, corregir hallazgos o solicitar una excepcion |
| [00 — Referencia del sistema](docs/tutorials/00-system-reference.md) | Cuando se ejecuta cada proceso, diagramas de flujo, SLSA y canales de reporte |
| [01 — Proteccion de Repositorios](docs/tutorials/01-repository-protection.md) | Visibilidad, GHAS, secret scanning y push protection |
| [02 — Proteccion de Ramas](docs/tutorials/02-branch-protection.md) | Branch protection rules, rulesets y configuracion avanzada |
| [03 — Roles y Permisos](docs/tutorials/03-roles-and-permissions.md) | GitHub roles, teams y permisos granulares en la organizacion |
| [04 — Aprobacion de Pull Requests](docs/tutorials/04-pull-request-approvals.md) | CODEOWNERS, required reviews y procesos de aprobacion |
| [05 — SLSA en Pipelines](docs/tutorials/05-slsa-pipelines.md) | Supply chain integrity con SLSA Level 3 |
| [06 — Activacion de Dependabot](docs/tutorials/06-dependabot-activation.md) | Dependabot alerts, security updates y version updates |
| [07 — Activacion de Semgrep](docs/tutorials/07-semgrep-activation.md) | Integracion SARIF, Code Scanning y gestion de reglas |
| [08 — Gestion de Excepciones](docs/tutorials/08-exception-management.md) | Falsos positivos, excepciones y flujo de aprobacion |
| [09 — Security Gates](docs/tutorials/09-security-gates.md) | Bloqueo de PRs por vulnerabilidades criticas y altas |
| [10 — Reporting de Seguridad](docs/tutorials/10-reporting.md) | Dashboards, Job Summaries y reportes automaticos |
| [11 — Gobierno de Vulnerabilidades](docs/tutorials/11-vulnerability-governance.md) | SLAs, ownership, escalado, compliance y metricas del programa |

---

## Que necesitas segun tu plan y tipo de repositorio

No todas las funcionalidades estan disponibles en todos los planes de GitHub. Esta tabla indica que puede usar cada organizacion sin coste adicional y que requiere GitHub Advanced Security (GHAS) o un plan de pago.

### Por plan de organizacion

| Funcionalidad | GitHub Free (org) | GitHub Team | GitHub Enterprise / GHAS |
|---------------|:-----------------:|:-----------:|:-------------------------:|
| Workflows reutilizables (Semgrep via este repo) | Si | Si | Si |
| Security gates en PRs | Si | Si | Si |
| Excepciones centralizadas | Si | Si | Si |
| SLSA Level 3 en releases | Si | Si | Si |
| Dependabot alerts | Si | Si | Si |
| Dependabot security updates (PRs automaticos) | Si | Si | Si |
| Secret Scanning (deteccion) | Solo repos publicos | Solo repos publicos | Si — todos los repos |
| Push Protection (bloqueo al hacer push) | Solo repos publicos | Solo repos publicos | Si — todos los repos |
| Code Scanning via SARIF (Security tab) | Solo repos publicos | Solo repos publicos | Si — todos los repos |
| Code Scanning alerts API | Solo repos publicos | Solo repos publicos | Si — todos los repos |
| CodeQL (herramienta de GitHub) | Solo repos publicos | Solo repos publicos | Si — todos los repos |
| GitHub Pages (para los portales de documentacion) | Solo repos publicos | Solo repos publicos | Si — repos privados tambien |
| OpenSSF Scorecard | Si (repo debe ser publico) | Si (repo debe ser publico) | Si |
| Required reviewers en branch protection | Si | Si | Si |
| Repository Rulesets | Si | Si | Si + Organization Rulesets |
| Organization Rulesets (una regla para todos los repos) | No | No | Si |
| Security Overview (vista agregada de la org) | No | No | Si |
| Dependabot grouping (agrupa PRs de actualizacion) | Si | Si | Si |

> **En la practica para `jgutierrezdtt`:** con repos publicos en el plan gratuito se obtiene el 90% de las funcionalidades de este sistema. Las unicas limitaciones son Secret Scanning en repos privados y el Security tab con SARIF. Semgrep, los gates, las excepciones, SLSA y Dependabot funcionan igual en cualquier plan.

### Por tipo de repositorio (dentro de la misma org)

| Funcionalidad | Repo publico | Repo privado (sin GHAS) | Repo privado (con GHAS) |
|---------------|:------------:|:-----------------------:|:-----------------------:|
| Semgrep via workflow reutilizable | Si | Si | Si |
| Security gate en PR | Si | Si | Si |
| SARIF en Security tab | Si | No (silencioso — no da error) | Si |
| Secret Scanning | Si | No | Si |
| Push Protection | Si | No | Si |
| GitHub Pages para documentacion | Si | No | Si |
| Dependabot alerts | Si | Si | Si |
| SLSA en releases | Si | Si | Si |

> **Comportamiento cuando SARIF falla silenciosamente en repos privados sin GHAS:** el step de upload de SARIF tiene `continue-on-error: true` en el workflow, asi que el pipeline no falla. Los hallazgos de Semgrep siguen apareciendo en el comentario del PR y en el Job Summary — solo no aparecen en el Security tab.

### Lo que necesitas instalar o configurar una unica vez

| Requisito | Donde configurarlo | Quien lo hace | Sin esto que pasa |
|-----------|-------------------|---------------|-------------------|
| `EXCEPTIONS_READER_TOKEN` en cada repo consumer | Settings > Secrets del repo | Security team o dev | El workflow corre pero sin filtrar excepciones — puede generar falsos positivos bloqueantes |
| `DEPENDABOT_CHECK_TOKEN` en cada repo consumer | Settings > Secrets del repo | Security team o dev | El check de Dependabot no puede leer las alertas — falla con 403 |
| `SEMGREP_APP_TOKEN` | Settings > Secrets del repo | Security team | Opcional — sin el no hay Semgrep Cloud Platform, pero el escaneo local funciona igual |
| Branch protection con required checks | Settings > Branches del repo | Security team o Tech Lead | El gate existe pero el dev puede mergear aunque falle |
| Dependabot habilitado en el repo | Settings > Security del repo | Dev o Tech Lead | No se generan alertas de dependencias vulnerables |
| `security-platform` y `security-exceptions` publicos | Settings > Visibility | Security team | Los repos consumers no pueden llamar a los workflows reutilizables (llamadas cross-repo requieren repos publicos en el plan gratuito) |

---

## Responsabilidades por equipo

Las tareas de este sistema se distribuyen entre tres equipos. No se repiten entre ellos — cada equipo es responsable de lo suyo sin dependencias ambiguas.

### Equipo de Desarrollo

Son los propietarios de cada repositorio consumer. Su relacion con la plataforma es como usuarios: reciben el feedback, corrigen su codigo y solicitan excepciones cuando es necesario.

**En el dia a dia:**
- Leer el comentario de Semgrep en los PRs y corregir los hallazgos antes de solicitar review
- Mergear los PRs de Dependabot antes de que venzan los SLAs (CRITICAL 24h, HIGH 72h)
- Cuando un hallazgo es un falso positivo, abrir el issue de excepcion en lugar de desactivar la herramienta
- Informar al Tech Lead si un SLA no es realista dado el contexto del proyecto

**Al integrar un repo nuevo:**
- Usar `security-consumer-template` como base (repos nuevos) o crear `.github/workflows/security.yml` (repos existentes)
- Anadir los secrets `EXCEPTIONS_READER_TOKEN` y `DEPENDABOT_CHECK_TOKEN`
- Habilitar Dependabot en Settings > Security del repo
- Abrir un PR de prueba para validar que el workflow funciona

**Lo que NO hacen:**
- Modificar las reglas de Semgrep o los umbrales del security gate
- Aprobar sus propias excepciones
- Deshabilitar el workflow de seguridad

---

### Equipo de Gobierno de GitHub (Platform / DevOps)

Son los administradores de la organizacion en GitHub. Gestionan la infraestructura que hace posible el sistema: permisos, tokens, visibilidad de repos y configuracion a nivel de org.

**Configuracion inicial (una sola vez):**
- Hacer `security-platform` y `security-exceptions` publicos para que los workflows cross-repo funcionen en el plan gratuito
- Configurar `security-consumer-template` con el flag `is_template: true`
- Crear el GitHub Team `security-team` con los miembros correctos
- Configurar el GitHub Environment `production` si se usan deployment gates
- Establecer Organization Rulesets si la org tiene GitHub Enterprise (para que branch protection aplique a todos los repos sin configurarlo uno a uno)

**Mantenimiento continuo:**
- Rotar los fine-grained PATs antes de su expiracion (`EXCEPTIONS_READER_TOKEN`, `DEPENDABOT_CHECK_TOKEN`) y actualizar los secrets en todos los repos afectados
- Añadir nuevos repos al fichero `config/monitored-repos.txt` de `security-platform` para que aparezcan en el dashboard semanal
- Revisar los issues de `detect-unconfigured-repos` (lunes) y coordinar con los equipos de desarrollo para completar la configuracion
- Gestionar el acceso de colaboradores externos que necesiten usar los workflows

**Lo que NO hacen:**
- Decidir la politica de excepciones (eso es del security team)
- Modificar las reglas de Semgrep
- Aprobar o rechazar excepciones de seguridad

---

### Equipo de Seguridad

Son los duenos de la politica de seguridad. Controlan que se puede escanear, que bloquea y que puede ser excepcionado. Son los unicos que pueden fusionar cambios en los archivos criticos de `security-platform` (CODEOWNERS lo garantiza).

**Politica y reglas:**
- Definir y mantener las reglas Semgrep en `config/semgrep/rules.yml` — anadir, ajustar severidades y retirar reglas siguiendo el proceso del [Tutorial 07](docs/tutorials/07-semgrep-activation.md)
- Decidir los umbrales del security gate (`fail-on-severity`) y cuando un repo puede operar en modo `report-only`
- Definir los SLAs de remediacion y comunicarlos a los Tech Leads
- Revisar y actualizar la politica de excepciones cuando cambia el contexto de riesgo

**Gestion de excepciones:**
- Revisar y aprobar o rechazar cada solicitud de excepcion en menos de 48h laborables
- Fusionar el PR a `security-exceptions` cuando se aprueba una excepcion
- Revisar semanalmente las excepciones proximas a vencer y notificar a los equipos afectados
- Detectar patrones: si una regla genera > 5 excepciones del mismo tipo, evaluar si la regla necesita ajuste

**Supervision y respuesta:**
- Revisar el dashboard semanal del lunes y actuar sobre los hallazgos fuera de SLA
- Escalar a los Tech Leads los hallazgos CRITICAL que no se han resuelto en 24h
- Diferenciar entre vulnerabilidad ordinaria e incidente de seguridad y activar el runbook de incidentes cuando corresponde
- Preparar el paquete de evidencia para auditorias externas

**Mantenimiento de la plataforma:**
- Actualizar `semgrep==1.70.0` y las versiones de las GitHub Actions cuando haya nuevas versiones relevantes
- Revisar el OpenSSF Scorecard de `security-platform` mensualmente y mejorar la puntuacion
- Aprobar cualquier PR que modifique `.github/workflows/reusable/` — requiere 2 aprobaciones del security team

**Lo que NO hacen:**
- Configurar repos individuales de los equipos de desarrollo (eso es de desarrollo o governance)
- Gestionar los tokens o secrets a nivel de org (eso es de governance)
- Aprobar sus propios PRs en `security-platform` (se requieren 2 revisores distintos)

---

## Arquitectura del Sistema

El principio central es simple: **las reglas viven en un sitio, los repos solo llaman**.

```
jgutierrezdtt/
 ├── security-platform/          ← Este repo — reglas, workflows, tutoriales
 │    └── .github/workflows/reusable/
 │         ├── semgrep-scan.yml       ← logica de escaneo
 │         ├── dependabot-check.yml   ← logica de dependencias
 │         └── slsa-build.yml         ← firma de artefactos
 │
 ├── security-consumer-template/  ← Template GitHub para nuevos repos
 │    └── .github/workflows/
 │         └── security.yml           ← unico archivo que necesita cada repo
 │
 ├── security-example-app/        ← Tutorial funcional — ejemplo vivo
 │
 ├── security-exceptions/         ← Registro de excepciones (read-only)
 │    ├── exceptions/global/
 │    └── exceptions/by-repo/
 │
 └── tu-repo/                     ← Cualquier repositorio consumer
      └── .github/workflows/
           └── security.yml  ──────► llama a security-platform@main
```

### Como funciona el modelo de actualizacion

Cuando el security team actualiza una regla de Semgrep o cambia un umbral en
`security-platform`, **todos los repos consumers lo reciben automaticamente**
en su siguiente ejecucion. No hay nada que sincronizar ni actualizar en los repos consumers.

El unico archivo que existe en cada repo consumer es un `security.yml` de ~15 lineas
que simplemente llama a este repo:

```yaml
jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
  dependabot:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/dependabot-check.yml@main
```

Ese archivo no cambia nunca. Las actualizaciones de seguridad no requieren ningun
PR en los repos consumers.

---

## Como integrar un nuevo repositorio

### Repos nuevos — un clic, sin configuracion manual

[security-consumer-template](https://github.com/jgutierrezdtt/security-consumer-template)
es un GitHub Template Repository. Para crear un nuevo repo con los controles de seguridad ya activos:

1. Ir a [github.com/jgutierrezdtt/security-consumer-template](https://github.com/jgutierrezdtt/security-consumer-template)
2. Pulsar **Use this template** > **Create a new repository**
3. Dar nombre y crear el repositorio

Listo. El workflow de seguridad se ejecuta desde el primer PR. No hay archivos que copiar ni scripts que lanzar.

### Repos existentes — anadir un archivo

Para repos que ya existen, el unico paso es crear `.github/workflows/security.yml` con este contenido:

```yaml
name: Security

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    secrets:
      EXCEPTIONS_READER_TOKEN: ${{ secrets.EXCEPTIONS_READER_TOKEN }}
      SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

  dependabot:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/dependabot-check.yml@main
    secrets:
      DEPENDABOT_CHECK_TOKEN: ${{ secrets.DEPENDABOT_CHECK_TOKEN }}
```

Ese archivo no volvera a necesitar modificaciones. Cualquier cambio en las reglas
o umbrales se hace aqui en security-platform y se propaga automaticamente.

### Secrets necesarios en cada repo consumer

| Secret | Como obtenerlo |
|--------|----------------|
| `EXCEPTIONS_READER_TOKEN` | Fine-grained PAT: Contents read-only en security-exceptions |
| `DEPENDABOT_CHECK_TOKEN` | Fine-grained PAT: Security events read en el repo |
| `SEMGREP_APP_TOKEN` | Opcional — Semgrep Cloud Platform |

### Deteccion automatica de repos sin configurar

El workflow [detect-unconfigured-repos.yml](.github/workflows/detect-unconfigured-repos.yml)
se ejecuta cada lunes y crea un GitHub Issue con la lista de repos que aun no tienen
`security.yml`. El security team recibe la notificacion y puede actuar sin necesidad
de ejecutar ningun comando.

---

## Quickstart

Ver [security-consumer-template](https://github.com/jgutierrezdtt/security-consumer-template)
y [security-example-app](https://github.com/jgutierrezdtt/security-example-app)
para ejemplos funcionales completos.

Resumen de 3 pasos para un repo existente:

**1. Crear `.github/workflows/security.yml`** (ver seccion anterior)

**2. Anadir secrets**
```bash
gh secret set EXCEPTIONS_READER_TOKEN --repo jgutierrezdtt/tu-repo
gh secret set DEPENDABOT_CHECK_TOKEN  --repo jgutierrezdtt/tu-repo
```

**3. Abrir un PR de prueba** — el workflow se ejecuta automaticamente

---

## Estado de Seguridad de la Organización

> **Actualizado automáticamente** cada domingo a las 02:00 UTC por el [workflow de reporte](/.github/workflows/org-security-report.yml).  
> Última actualización: `<!-- LAST_REPORT_DATE -->`

### Resumen por repositorio

| Repositorio | Rama | Semgrep | Dependabot | SLSA | Críticas | Altas | Medias | Último Análisis |
|-------------|------|---------|------------|------|----------|-------|--------|-----------------|
| `security-platform` | `main` |  Activo |  Activo |  L3 | 0 | 0 | 0 | <!-- DATE --> |
| `security-exceptions` | `main` |  Activo |  Activo | — | 0 | 0 | 0 | <!-- DATE --> |
| *Añadir repos aquí* | | | | | | | | |

> **Nota**: Esta tabla se genera automáticamente. Para añadir un repositorio al reporte, consulta [docs/tutorials/10-reporting.md](docs/tutorials/10-reporting.md).

### Leyenda de estados

| Símbolo | Significado |
|---------|-------------|
|  Activo | Habilitado y funcionando correctamente |
|  Parcial | Configurado pero con advertencias |
|  Inactivo | No configurado o con errores |
| — | No aplica |

---

## Workflows Reutilizables

### `reusable/semgrep-scan.yml`
Escaneo SAST con Semgrep, integración con excepciones, tabla visual en PR y security gate.

**Inputs:**

| Input | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `scan-scope` | `string` | `diff` | `full` o `diff` |
| `fail-on-severity` | `string` | `high` | Severidad mínima para fallar: `critical`, `high`, `medium`, `low` |
| `upload-sarif` | `boolean` | `true` | Subir SARIF al Security tab de GitHub |
| `create-issues` | `boolean` | `false` | Crear GitHub Issues para cada hallazgo |
| `exceptions-repo` | `string` | `jgutierrezdtt/security-exceptions` | Repo de excepciones |

**Secrets:**

| Secret | Requerido | Descripción |
|--------|-----------|-------------|
| `SEMGREP_APP_TOKEN` | No | Token de Semgrep Cloud Platform |
| `EXCEPTIONS_READER_TOKEN` | Sí | Fine-grained PAT (read-only) al repo de excepciones |

---

### `reusable/dependabot-check.yml`
Valida el estado de las alertas de Dependabot y bloquea el pipeline si hay vulnerabilidades críticas no resueltas.

---

### `reusable/slsa-build.yml`
Genera provenance SLSA Level 3 para artefactos de release usando el generador oficial de la SLSA Framework.

---

## Templates disponibles

```
templates/consumer/
 .github/
    CODEOWNERS                    ← Propietarios de código
    dependabot.yml                ← Configuración de Dependabot
    workflows/
        security.yml              ← Pipeline principal de seguridad
        dependabot-check.yml      ← Validación de Dependabot en PRs
        release.yml               ← Release con SLSA
 config/
     semgrep/
         .semgrepignore            ← Patrones de exclusión
```

---

## Referencias

- [Semgrep Documentation](https://semgrep.dev/docs/)
- [SLSA Framework](https://slsa.dev/)
- [GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

## Contribuciones

Solo el equipo `@jgutierrezdtt/security-team` puede aprobar cambios en este repositorio.  
Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para el proceso de contribución.

## Licencia

Uso interno — jgutierrezdtt. Consulta [LICENSE](LICENSE).
