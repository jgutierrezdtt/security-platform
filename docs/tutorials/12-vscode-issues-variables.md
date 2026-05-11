# Tutorial 12 — VS Code, GitHub Issues y Variables de los Pipelines

> **Audiencia**: Desarrolladores, DevSecOps engineers  
> **Nivel**: Básico-Intermedio  
> **Tiempo estimado**: 40 minutos

---

## ¿Qué cubre este tutorial?

1. **Ver alertas de seguridad directamente en VS Code** — usando la extensión GitHub Pull Requests & Issues
2. **Gestionar issues de seguridad desde VS Code** — sin salir del editor
3. **Creación automática de issues desde los pipelines** — Semgrep y Dependabot crean issues para hallazgos CRITICAL/HIGH
4. **Referencia completa de todas las variables** — inputs, secrets y outputs de cada workflow reutilizable

---

## Parte 1 — VS Code: Ver y gestionar issues de seguridad

### 1.1 Instalar la extensión GitHub Pull Requests & Issues

La extensión oficial de GitHub para VS Code permite ver issues, PRs y alertas de Code Scanning sin salir del editor.

**Instalación:**

1. Abre VS Code
2. Ve a **Extensions** (`Cmd+Shift+X` en macOS, `Ctrl+Shift+X` en Windows/Linux)
3. Busca: `GitHub Pull Requests`
4. Instala: **GitHub Pull Requests and Issues** (editor: GitHub)
5. Haz clic en **Sign in to GitHub** en la barra de estado inferior

O desde la terminal:

```bash
code --install-extension GitHub.vscode-pull-request-github
```

### 1.2 Ver Issues de seguridad en VS Code

Una vez instalada la extensión, verás en la barra lateral izquierda el icono de GitHub (Octocat).

**Navegar a Issues:**

1. Haz clic en el icono de **GitHub** en la barra lateral
2. Expande la sección **Issues**
3. Verás todos los issues del repositorio actual, agrupados por estado

**Filtrar por issues de seguridad:**

Los issues creados por nuestros pipelines llevan etiquetas específicas:

| Etiqueta | Origen | Qué contiene |
|----------|--------|-------------|
| `security` | Semgrep + Dependabot | Todos los hallazgos de seguridad |
| `semgrep` | Workflow de Semgrep | Vulnerabilidades en código (SAST) |
| `dependabot-alert` | Workflow de Dependabot | Dependencias vulnerables |
| `critical` | Semgrep + Dependabot | Solo hallazgos críticos |
| `high` | Semgrep + Dependabot | Solo hallazgos altos |
| `direct-dependency` | Dependabot | Dependencias directas (las que defines en requirements.txt, package.json, etc.) |

Para filtrar, usa el campo de búsqueda de issues o añade `?labels=security` a la URL del repo en GitHub.

### 1.3 Ver Code Scanning alerts en VS Code

Los resultados SARIF de Semgrep se suben al **Security tab** de GitHub y también aparecen como diagnósticos en VS Code si tienes habilitada la integración.

**Activar alertas de Code Scanning en el editor:**

1. Abre la **Command Palette** (`Cmd+Shift+P`)
2. Busca: `GitHub: Focus on Code Scanning`
3. Aparecerá un panel con las alertas activas del repositorio

Alternativamente, las alertas aparecen como **ondas rojas/amarillas en el editor** si tienes habilitado el language server con las reglas de Semgrep localmente.

### 1.4 Ver Pull Requests con checks fallidos

Cuando un PR falla el security gate:

1. Abre la extensión GitHub en la barra lateral
2. Sección **Pull Requests** → busca el PR con ⚠️ o ❌
3. Haz clic en el PR para ver el detalle
4. Verás los **Status Checks** con el resultado de Semgrep y Dependabot
5. Haz clic en un check fallido → se abre la pestaña de Actions directamente

**Ver el comentario de Semgrep en el PR desde VS Code:**

En la vista del PR dentro de la extensión, verás el comentario generado automáticamente por el pipeline con la tabla de hallazgos, el badge de estado y el enlace a la guía `pr-blocked-guide.md`.

### 1.5 Crear un issue de seguridad manualmente desde VS Code

Cuando encuentras un problema de seguridad que quieres rastrear:

1. En la barra lateral → sección **Issues** → icono **+** (Create Issue)
2. Título: `[Security] Descripción del problema`
3. Cuerpo: descripción, pasos para reproducir, impacto
4. Etiquetas: añade `security` y la severidad (`critical`, `high`, `medium`)
5. Asigna al responsable del componente

O desde la terminal con `gh`:

```bash
gh issue create \
  --title "[Security] SQL Injection en módulo de usuarios" \
  --body "Descripción del hallazgo..." \
  --label "security,high" \
  --assignee "@me"
```

---

## Parte 2 — Creación automática de Issues desde los pipelines

### 2.1 Issues automáticos de Semgrep

El workflow `reusable-semgrep-scan.yml` puede crear issues automáticamente para cada hallazgo CRITICAL/HIGH. Está **desactivado por defecto** para evitar spam — actívalo cuando el equipo esté listo para gestionar el volumen.

**Activar en tu `security.yml`:**

```yaml
jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-semgrep-scan.yml@main
    with:
      create-issues: true          # ← Activa la creación de issues
      fail-on-severity: high
    secrets: inherit
```

**Qué incluye cada issue creado por Semgrep:**

```markdown
## 🔐 Vulnerabilidad detectada por Semgrep

**Severidad**: HIGH
**Regla**: `python.sqlalchemy.security.sqlalchemy-execute-raw-query`
**Archivo**: `src/app.py:12`
**Commit**: `a1b2c3d4`

### Descripción
Avoiding SQL string concatenation: untrusted input concatenated with raw SQL...

### Remediación
Consulta la documentación de la regla en: https://semgrep.dev/r/python.sqlalchemy...

### ¿Falso positivo?
Si crees que esto es un falso positivo, abre una solicitud de excepción en:
`jgutierrezdtt/security-exceptions`

---
*Generado automáticamente por el pipeline de Semgrep.*
```

**Etiquetas aplicadas**: `security`, `semgrep`, `high` (o `critical`)

> **Nota**: El workflow comprueba si ya existe un issue abierto con el mismo título antes de crear uno nuevo, para evitar duplicados entre ejecuciones.

### 2.2 Issues automáticos de Dependabot (CRITICAL/HIGH en dependencias directas)

El workflow `reusable-dependabot-check.yml` puede crear issues para alertas críticas y altas de **dependencias directas** (las que declaras explícitamente en tu `requirements.txt`, `package.json`, `pom.xml`, etc.).

Las dependencias **transitivas** (instaladas por tus dependencias) se reportan en el resumen pero **no generan issue individual** para evitar ruido — el equipo de seguridad las gestiona a nivel de plataforma.

**Activar en tu `security.yml`:**

```yaml
jobs:
  dependabot-check:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-dependabot-check.yml@main
    with:
      create-issues: true           # ← Activa la creación de issues
      create-issues-min-severity: high   # critical | high (default: high)
      direct-only: true             # Solo dependencias directas (default: true)
    secrets: inherit
```

**Qué incluye cada issue creado por Dependabot:**

```markdown
## 📦 Dependencia vulnerable detectada por Dependabot

**Paquete**: `requests==2.25.0`
**Ecosistema**: pip
**Severidad**: HIGH
**CVE**: CVE-2023-32681
**Tipo de dependencia**: Directa
**Alerta Dependabot**: #3

### Descripción del CVE
Requests forwards proxy-authorization headers to destination servers...

### Remediación
Actualiza a la versión parcheada:
- **Versión vulnerable**: `2.25.0`
- **Versión parcheada**: `2.31.0` o superior

Comando rápido:
pip install --upgrade requests

### Cómo actualizar
1. Modifica `requirements.txt`: cambia `requests==2.25.0` → `requests>=2.31.0`
2. Ejecuta `pip install -r requirements.txt`
3. Ejecuta tests: `pytest`
4. Abre un PR con el cambio

---
*Generado automáticamente. Ver alerta completa en: #3*
```

**Etiquetas aplicadas**: `security`, `dependabot-alert`, `high` (o `critical`), `direct-dependency`

### 2.3 Evitar duplicados entre ejecuciones

Ambos pipelines usan el **título del issue como clave de deduplicación**. Antes de crear un issue, el pipeline comprueba:

```bash
gh issue list --label "security" --state open --search "título del issue"
```

Si ya existe un issue abierto con ese título exacto, no se crea uno nuevo. Cuando la vulnerabilidad se remedia:

1. El pipeline lo detecta (hallazgo desaparece en el siguiente scan)
2. El issue se **cierra automáticamente** con un comentario de cierre
3. O el desarrollador lo cierra manualmente cuando hace el merge del fix

### 2.4 Gestionar el volumen de issues

Si activas `create-issues: true` en un repositorio con muchas vulnerabilidades pre-existentes, el primer run puede crear muchos issues. Estrategia recomendada:

```yaml
# Fase 1: Solo reportar (sin crear issues ni bloquear)
with:
  create-issues: false
  report-only: true

# Fase 2: Crear issues pero no bloquear el pipeline
with:
  create-issues: true
  report-only: true

# Fase 3: Crear issues Y bloquear en CRITICAL
with:
  create-issues: true
  fail-on-severity: critical

# Fase 4: Bloquear también en HIGH (estado objetivo)
with:
  create-issues: true
  fail-on-severity: high
```

---

## Parte 3 — Referencia completa de variables de los pipelines

### 3.1 Workflow: `reusable-semgrep-scan.yml`

#### Inputs (parámetros de configuración)

| Input | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `scan-scope` | string | `"diff"` | `diff`: solo archivos modificados en el PR (rápido). `full`: repositorio completo (recomendado en `main`). |
| `fail-on-severity` | string | `"high"` | Severidad mínima para bloquear el pipeline. Valores: `critical`, `high`, `medium`, `low`. |
| `upload-sarif` | boolean | `true` | Sube resultados SARIF al Security tab de GitHub (requiere GitHub Advanced Security). |
| `create-issues` | boolean | `false` | Crea GitHub Issues automáticamente para cada hallazgo CRITICAL/HIGH. |
| `exceptions-repo` | string | `"jgutierrezdtt/security-exceptions"` | Repositorio central donde se almacenan las excepciones aprobadas. Formato: `org/repo`. |
| `semgrep-rules` | string | `"p/default"` | Rulesets de Semgrep a aplicar, separados por espacio. Ejemplos: `p/default`, `p/owasp-top-ten`, ruta a archivo local `.github/config/semgrep/rules.yml`. |
| `report-only` | boolean | `false` | Si es `true`, el pipeline nunca falla aunque encuentre vulnerabilidades. Útil en ramas de feature durante la adopción inicial. |

#### Secrets (tokens de acceso)

| Secret | Obligatorio | Descripción | Cómo obtener |
|--------|-------------|-------------|--------------|
| `SEMGREP_APP_TOKEN` | No | Token de Semgrep Cloud Platform. Permite usar rulesets Pro (`p/security-audit`, `p/r2c-security-audit`) y ver resultados en el dashboard de Semgrep Cloud. Sin este token, solo se usan reglas open-source (`p/default`). | Crea una cuenta en semgrep.dev → Settings → Tokens |
| `EXCEPTIONS_READER_TOKEN` | No | Fine-grained PAT de GitHub con permiso `Contents: Read` en el repositorio `security-exceptions`. Permite filtrar falsos positivos aprobados por el security team. Sin este token, no se filtran excepciones y todos los hallazgos son activos. | GitHub → Settings → Developer settings → Fine-grained tokens |

#### Outputs (valores disponibles para jobs posteriores)

| Output | Tipo | Descripción |
|--------|------|-------------|
| `findings-count` | number | Total de hallazgos activos (después de filtrar excepciones). |
| `critical-count` | number | Número de hallazgos con severidad CRITICAL. |
| `high-count` | number | Número de hallazgos con severidad HIGH. |

#### Variables de entorno internas (usadas dentro del workflow)

Estas variables las gestiona el propio workflow y no se configuran desde fuera:

| Variable | Origen | Descripción |
|----------|--------|-------------|
| `GITHUB_OUTPUT` | GitHub Actions | Archivo especial donde el workflow escribe outputs para steps posteriores. |
| `GITHUB_STEP_SUMMARY` | GitHub Actions | Archivo para escribir el resumen visual que aparece en la pestaña Actions. |
| `GITHUB_SHA` | GitHub Actions | Hash completo del commit que disparó el workflow. |
| `GITHUB_REPOSITORY` | GitHub Actions | Nombre completo del repo: `owner/repo`. |
| `GITHUB_EVENT_NAME` | GitHub Actions | Tipo de evento: `push`, `pull_request`, `schedule`. |
| `GITHUB_BASE_REF` | GitHub Actions | Rama destino del PR (solo disponible en evento `pull_request`). Usado para el diff. |
| `GH_TOKEN` | Inyectado por Actions | Token automático para operaciones de la CLI `gh` (crear issues, comentar en PR). |

#### Permisos requeridos por el workflow

El workflow declara sus permisos explícitamente (principio de mínimo privilegio):

```yaml
permissions:
  contents: read           # Leer el código del repositorio (checkout)
  security-events: write   # Subir SARIF al Security tab de GitHub
  pull-requests: write     # Publicar comentario con los resultados en el PR
  issues: write            # Crear issues (solo si create-issues: true)
```

---

### 3.2 Workflow: `reusable-dependabot-check.yml`

#### Inputs (parámetros de configuración)

| Input | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `fail-on-critical` | boolean | `true` | Bloquea el pipeline si hay alertas críticas abiertas. |
| `fail-on-high` | boolean | `true` | Bloquea el pipeline si hay alertas altas abiertas. |
| `max-critical` | number | `0` | Número máximo de alertas críticas toleradas antes de fallar. `0` = ninguna. |
| `max-high` | number | `0` | Número máximo de alertas altas toleradas antes de fallar. `0` = ninguna. |
| `check-dependabot-enabled` | boolean | `true` | Verifica que el archivo `.github/dependabot.yml` existe en el repositorio. |
| `report-only` | boolean | `false` | Solo genera el reporte, sin bloquear el pipeline. |
| `create-issues` | boolean | `false` | Crea GitHub Issues automáticamente para alertas CRITICAL/HIGH en dependencias directas. |
| `create-issues-min-severity` | string | `"high"` | Severidad mínima para crear issue. Valores: `critical`, `high`. |
| `direct-only` | boolean | `true` | Solo crea issues para dependencias directas (declaradas explícitamente). Las transitivas se reportan en el resumen pero no generan issue individual. |

#### Secrets (tokens de acceso)

| Secret | Obligatorio | Descripción | Permisos necesarios |
|--------|-------------|-------------|---------------------|
| `DEPENDABOT_CHECK_TOKEN` | No | Fine-grained PAT para leer alertas de Dependabot vía API. Sin este token, el step se omite con un aviso pero el workflow no falla. | `Dependabot alerts: Read`, `Contents: Read` en el repo objetivo |

#### Outputs (valores disponibles para jobs posteriores)

| Output | Tipo | Valores posibles | Descripción |
|--------|------|-----------------|-------------|
| `dependabot-enabled` | string | `"true"`, `"false"`, `"skipped"` | Estado de Dependabot en el repositorio. `"skipped"` cuando no hay token. |
| `critical-alerts` | number | `0`-`N` | Número de alertas críticas abiertas actualmente. |
| `high-alerts` | number | `0`-`N` | Número de alertas altas abiertas actualmente. |
| `total-alerts` | number | `0`-`N` | Total de alertas abiertas (todas las severidades). |

#### Permisos requeridos

```yaml
permissions:
  contents: read       # Leer .github/dependabot.yml
  pull-requests: write # Publicar comentario con los resultados en el PR
  issues: write        # Crear issues (solo si create-issues: true)
```

---

### 3.3 Workflow: `reusable-slsa-build.yml`

Este workflow solo se activa en eventos de Release, no en PRs.

#### Inputs

| Input | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `artifact-name` | string | `"app"` | Nombre del artefacto construido que se firmará con SLSA. |
| `build-command` | string | — | Comando para construir el artefacto (ej: `make build`, `npm run build`). |

#### Secrets

| Secret | Obligatorio | Descripción |
|--------|-------------|-------------|
| — | — | SLSA Level 3 usa Sigstore keyless signing — no requiere tokens adicionales. |

---

### 3.4 Uso combinado: pasar outputs entre jobs

Puedes usar los outputs de un workflow como inputs de otro en el mismo `security.yml`:

```yaml
jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-semgrep-scan.yml@main
    with:
      scan-scope: full
      fail-on-severity: high
    secrets: inherit

  dependabot-check:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-dependabot-check.yml@main
    secrets: inherit

  # Job que usa los outputs de ambos
  security-summary:
    needs: [semgrep, dependabot-check]
    runs-on: ubuntu-latest
    steps:
      - name: Print security summary
        run: |
          echo "Semgrep findings: ${{ needs.semgrep.outputs.findings-count }}"
          echo "Semgrep critical: ${{ needs.semgrep.outputs.critical-count }}"
          echo "Semgrep high:     ${{ needs.semgrep.outputs.high-count }}"
          echo "Dependabot total: ${{ needs.dependabot-check.outputs.total-alerts }}"
          echo "Dependabot crit:  ${{ needs.dependabot-check.outputs.critical-alerts }}"
```

---

### 3.5 Ejemplo completo de `security.yml` con todas las opciones

```yaml
# .github/workflows/security.yml
# Ejemplo con TODAS las opciones configuradas explícitamente

name: Security
on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: "0 2 * * 1"   # Lunes a las 2am UTC

permissions:
  contents: read
  security-events: write
  pull-requests: write
  issues: write

jobs:
  semgrep:
    name: Semgrep SAST
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-semgrep-scan.yml@main
    permissions:
      contents: read
      security-events: write
      pull-requests: write
      issues: write
    with:
      # Escaneo diferencial en PRs, completo en main/schedule
      scan-scope: ${{ github.event_name == 'pull_request' && 'diff' || 'full' }}
      
      # Bloquear en HIGH y CRITICAL (no en MEDIUM/LOW)
      fail-on-severity: high
      
      # Subir al Security tab (requiere GHAS — gratis en repos públicos)
      upload-sarif: true
      
      # Crear issues automáticos para hallazgos HIGH/CRITICAL
      create-issues: false   # Cambiar a true cuando el equipo esté listo
      
      # Repositorio de excepciones aprobadas
      exceptions-repo: jgutierrezdtt/security-exceptions
      
      # Rulesets de Semgrep
      semgrep-rules: p/default
      
      # false = bloquear el pipeline si hay hallazgos
      report-only: false
    secrets: inherit

  dependabot-check:
    name: Dependabot Check
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-dependabot-check.yml@main
    permissions:
      contents: read
      pull-requests: write
      issues: write
    with:
      # Bloquear si hay alertas CRITICAL o HIGH sin resolver
      fail-on-critical: true
      fail-on-high: true
      
      # Tolerancia: 0 alertas permitidas antes de bloquear
      max-critical: 0
      max-high: 0
      
      # Verificar que .github/dependabot.yml existe
      check-dependabot-enabled: true
      
      # false = bloquear el pipeline
      report-only: false
      
      # Crear issues para dependencias directas vulnerables
      create-issues: false   # Requiere DEPENDABOT_CHECK_TOKEN configurado
      create-issues-min-severity: high
      direct-only: true
    secrets: inherit
```

---

## Parte 4 — Variables del `.github/dependabot.yml` explicadas

El archivo `dependabot.yml` controla cómo Dependabot actualiza las dependencias. Ejemplo comentado:

```yaml
# .github/dependabot.yml

version: 2

updates:
  # ── Dependencias Python ──────────────────────────────────────
  - package-ecosystem: "pip"           # pip | npm | maven | gradle | docker | etc.
    directory: "/"                     # Dónde está requirements.txt
    schedule:
      interval: "weekly"               # daily | weekly | monthly
      day: "monday"                    # Para weekly: día de la semana
      time: "09:00"                    # Hora UTC del check
    
    open-pull-requests-limit: 5        # Máximo de PRs abiertos simultáneamente
    
    labels:
      - "dependencies"
      - "security"
    
    assignees:
      - "security-team"
    
    # Agrupar todas las actualizaciones de seguridad en un solo PR
    groups:
      security-updates:
        patterns:
          - "*"
        update-types:
          - "patch"
          - "minor"
    
    # Ignorar actualizaciones de versiones mayor (pueden romper la API)
    ignore:
      - dependency-name: "django"
        update-types: ["version-update:semver-major"]
  
  # ── Acciones de GitHub Actions ───────────────────────────────
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

**Campos clave:**

| Campo | Descripción |
|-------|-------------|
| `package-ecosystem` | Gestor de paquetes: `pip`, `npm`, `maven`, `gradle`, `docker`, `github-actions`, `cargo`, `bundler`, `nuget`, `gomod`, `composer` |
| `directory` | Ruta al archivo de dependencias relativa a la raíz del repo. `/` para la raíz. |
| `interval: daily` | Comprueba actualizaciones cada día |
| `interval: weekly` | Comprueba una vez a la semana (el `day` especificado) |
| `open-pull-requests-limit` | Evita que Dependabot abra más PRs de los que el equipo puede revisar. Recomendado: 5-10 |
| `groups` | Agrupa múltiples actualizaciones en un único PR para reducir ruido |
| `ignore` | Lista de dependencias o rangos de versión que Dependabot no debe actualizar |

---

## Parte 5 — Secrets: cómo crearlos y dónde configurarlos

### 5.1 Crear un Fine-grained PAT para EXCEPTIONS_READER_TOKEN

```
1. GitHub.com → Settings (tuyo, no del repo)
2. Developer settings → Personal access tokens → Fine-grained tokens
3. "Generate new token"
4. Token name: security-platform-exceptions-reader
5. Expiration: 90 días (renovar con recordatorio en calendario)
6. Resource owner: jgutierrezdtt
7. Repository access: Only selected → security-exceptions
8. Repository permissions:
   - Contents: Read-only
   (dejar todo lo demás en "No access")
9. "Generate token" → Copia el token (solo se muestra una vez)
```

### 5.2 Crear un Fine-grained PAT para DEPENDABOT_CHECK_TOKEN

```
Mismos pasos, con estas diferencias:
4. Token name: security-platform-dependabot-reader
7. Repository access: Only selected → el repo donde se ejecuta el workflow
8. Repository permissions:
   - Contents: Read-only
   - Dependabot alerts: Read-only
```

### 5.3 Añadir el secret al repositorio

```bash
# Via CLI (recomendado — no expone el valor en el historial de terminal)
gh secret set EXCEPTIONS_READER_TOKEN --repo jgutierrezdtt/mi-repo

# Pega el token cuando lo pida (la terminal no lo muestra)
```

O via UI:
```
Repo → Settings → Secrets and variables → Actions
→ "New repository secret"
→ Name: EXCEPTIONS_READER_TOKEN
→ Secret: [pega el token]
```

### 5.4 Verificar qué secrets están configurados

```bash
# Lista los nombres (nunca los valores — GitHub no los muestra)
gh secret list --repo jgutierrezdtt/mi-repo
```

---

## Resumen rápido

| Quiero... | Input/Secret | Workflow |
|-----------|-------------|---------|
| Escanear solo los archivos del PR | `scan-scope: diff` | semgrep |
| Escanear todo el repo | `scan-scope: full` | semgrep |
| No bloquear el pipeline nunca | `report-only: true` | semgrep / dependabot |
| Bloquear solo en vulnerabilidades críticas | `fail-on-severity: critical` | semgrep |
| Crear issues automáticamente | `create-issues: true` | semgrep / dependabot |
| Usar reglas de Semgrep Pro | Configura `SEMGREP_APP_TOKEN` | semgrep |
| Filtrar falsos positivos | Configura `EXCEPTIONS_READER_TOKEN` | semgrep |
| Leer alertas de Dependabot en el pipeline | Configura `DEPENDABOT_CHECK_TOKEN` | dependabot |
| Ver issues en VS Code | Instala `GitHub.vscode-pull-request-github` | — |
| Ver alertas SARIF en VS Code | Abre Command Palette → "GitHub: Focus on Code Scanning" | — |
