# Security Platform — jgutierrezdtt

> **Repositorio central de seguridad** para la organización `jgutierrezdtt`.  
> Proporciona workflows reutilizables, reglas Semgrep, tutoriales y el template base para cualquier repositorio nuevo.

---

## Índice de tutoriales

| # | Tutorial | Descripción |
|---|----------|-------------|| 00 | [Referencia del sistema](docs/tutorials/00-system-reference.md) | Cuando se ejecuta cada proceso, diagramas de flujo, SLSA y como se reportan los resultados || 01 | [Protección de Repositorios](docs/tutorials/01-repository-protection.md) | Configuración de visibilidad, GHAS, secret scanning y push protection |
| 02 | [Protección de Ramas](docs/tutorials/02-branch-protection.md) | Branch protection rules, rulesets y configuración avanzada |
| 03 | [Roles y Permisos](docs/tutorials/03-roles-and-permissions.md) | GitHub roles, teams y permisos granulares en la organización |
| 04 | [Aprobación de Pull Requests](docs/tutorials/04-pull-request-approvals.md) | CODEOWNERS, required reviews y procesos de aprobación |
| 05 | [SLSA en Pipelines](docs/tutorials/05-slsa-pipelines.md) | Supply chain integrity con SLSA Level 3 usando el workflow oficial |
| 06 | [Activación de Dependabot](docs/tutorials/06-dependabot-activation.md) | Dependabot alerts, security updates y version updates |
| 07 | [Activación de Semgrep](docs/tutorials/07-semgrep-activation.md) | Integración de Semgrep, SARIF, Code Scanning y gestión de reglas |
| 08 | [Gestión de Excepciones](docs/tutorials/08-exception-management.md) | Falsos positivos, excepciones y flujo de aprobación |
| 09 | [Security Gates](docs/tutorials/09-security-gates.md) | Bloqueo de PRs por vulnerabilidades críticas y altas |
| 10 | [Reporting de Seguridad](docs/tutorials/10-reporting.md) | Dashboards, tablas visuales en Actions y reportes automáticos |

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
