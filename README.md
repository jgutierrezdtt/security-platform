# Security Platform — amazing-protection

> **Repositorio central de seguridad** para la organización `amazing-protection`.  
> Proporciona workflows reutilizables, políticas de gobernanza, documentación técnica y templates listos para usar en cualquier repositorio de la organización.

---

## Índice de tutoriales

| # | Tutorial | Descripción |
|---|----------|-------------|
| 01 | [Protección de Repositorios](docs/tutorials/01-repository-protection.md) | Configuración de visibilidad, GHAS, secret scanning y push protection |
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

```
amazing-protection/
 security-platform/          ← Este repositorio
    .github/workflows/
       reusable/           ← Workflows llamados por todos los repos
           semgrep-scan.yml
           dependabot-check.yml
           slsa-build.yml
    config/semgrep/         ← Reglas Semgrep centralizadas
    docs/tutorials/         ← 10 tutoriales técnicos
    templates/consumer/     ← Templates listos para copiar

 security-exceptions/        ← Registro de excepciones (read-only)
     exceptions/global/      ← Falsos positivos globales
     exceptions/by-repo/     ← Excepciones por repositorio
     schemas/                ← JSON Schema de validación
```

---

## Onboarding de repositorios

### Escalar a 200 repos existentes (onboarding masivo)

El script `scripts/bulk-onboard.py` aplica los templates de seguridad a todos los repos de la organización y abre un PR en cada uno:

```bash
# Requiere: pip install requests && export GH_TOKEN=<token-con-contents:write>

# Onboarding de todos los repos (excluye archivados y forks)
python3 scripts/bulk-onboard.py --org amazing-protection

# Solo repos específicos
python3 scripts/bulk-onboard.py --org amazing-protection --repos-file repos.txt

# Simular sin crear PRs (recomendado antes de lanzar en producción)
python3 scripts/bulk-onboard.py --org amazing-protection --dry-run

# Limitar para pruebas (p.ej: probar con 5 repos)
python3 scripts/bulk-onboard.py --org amazing-protection --limit 5
```

El script:
- Detecta automáticamente todos los repos no configurados
- Crea la rama `security/onboarding-platform` en cada repo
- Aplica los 5 consumer templates (workflows, dependabot, CODEOWNERS, PR template, .semgrepignore)
- Abre un PR explicativo listo para revisar y mergear
- Actualiza `config/monitored-repos.txt` automáticamente
- Evita duplicados si ya existe un PR de onboarding o el repo ya está configurado

### Detección automática de repos nuevos

El workflow [detect-unconfigured-repos.yml](.github/workflows/detect-unconfigured-repos.yml) se ejecuta cada lunes y:
- Detecta repos sin `.github/workflows/security.yml`
- Crea automáticamente un GitHub Issue con la lista de repos pendientes
- El issue asigna al `security-team` para que lancen el onboarding

Para forzar una comprobación inmediata:
```bash
gh workflow run detect-unconfigured-repos.yml --repo amazing-protection/security-platform
```

---

## Quickstart para nuevos repositorios

### 1. Copiar los templates al repositorio

```bash
# Desde la raíz de tu repositorio
PLATFORM=amazing-protection/security-platform

gh api repos/${PLATFORM}/contents/templates/consumer \
  --jq '.[] | .path' | while read file; do
  gh api repos/${PLATFORM}/contents/${file} \
    --jq '.content' | base64 -d > "${file#templates/consumer/}"
done
```

### 2. Configurar los secretos requeridos

```bash
# Token de lectura del repo de excepciones (Fine-grained PAT o GitHub App)
gh secret set EXCEPTIONS_READER_TOKEN --repo tu-org/tu-repo

# Token de Semgrep Cloud Platform (opcional pero recomendado)
gh secret set SEMGREP_APP_TOKEN --repo tu-org/tu-repo
```

### 3. Habilitar Code Scanning

```bash
gh api repos/tu-org/tu-repo/code-scanning/default-setup \
  -X PATCH \
  --field state=configured \
  --field query_suite=security-extended
```

### 4. Llamar al workflow reutilizable

```yaml
# .github/workflows/security.yml en tu repositorio
jobs:
  semgrep:
    uses: amazing-protection/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    secrets:
      SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}
      EXCEPTIONS_READER_TOKEN: ${{ secrets.EXCEPTIONS_READER_TOKEN }}
```

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
| `exceptions-repo` | `string` | `amazing-protection/security-exceptions` | Repo de excepciones |

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

Solo el equipo `@amazing-protection/security-team` puede aprobar cambios en este repositorio.  
Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para el proceso de contribución.

## Licencia

Uso interno — amazing-protection. Consulta [LICENSE](LICENSE).
