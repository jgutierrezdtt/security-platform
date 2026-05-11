# Tutorial 06 — Activación de Dependabot

> **Audiencia**: Desarrolladores, DevSecOps engineers  
> **Nivel**: Básico-Intermedio  
> **Tiempo estimado**: 30 minutos

---

## ¿Qué es Dependabot?

Dependabot es el sistema de gestión de dependencias de GitHub. Tiene tres componentes:

| Componente | Función | Configuración |
|-----------|---------|--------------|
| **Dependabot Alerts** | Detecta dependencias con CVEs conocidos | Settings del repo |
| **Dependabot Security Updates** | Crea PRs automáticos para parchear vulnerabilidades | Settings del repo |
| **Dependabot Version Updates** | Mantiene dependencias actualizadas proactivamente | `.github/dependabot.yml` |

---

## 1. Habilitar Dependabot Alerts y Security Updates

### 1.1 Via GitHub UI

1. Ve a `Settings` → `Code security and analysis`
2. Habilita:
   - ✅ **Dependabot alerts**
   - ✅ **Dependabot security updates**

### 1.2 Via API

```bash
# Habilitar alerts y security updates
gh api repos/jgutierrezdtt/mi-repo \
  -X PATCH \
  --field security_and_analysis='{
    "dependabot_security_updates": {"status": "enabled"}
  }'

# Verificar estado
gh api repos/jgutierrezdtt/mi-repo \
  --jq '.security_and_analysis.dependabot_security_updates'
```

### 1.3 Habilitar en toda la organización

```bash
# Para todos los repos de la org
gh api orgs/jgutierrezdtt \
  -X PATCH \
  --field default_repository_permission=none

# Configurar política de Dependabot para la org
gh api orgs/jgutierrezdtt/dependabot/alerts \
  --jq '.[0:5]'
```

---

## 2. Configurar `.github/dependabot.yml`

Este archivo controla **qué** actualiza Dependabot y **cuándo**:

```yaml
# .github/dependabot.yml
version: 2

updates:
  # ─── GitHub Actions ────────────────────────────────
  # CRÍTICO: mantiene las acciones pinned por hash seguras
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "Europe/Madrid"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "ci"
      include: "scope"
    groups:
      # Agrupa actualizaciones de acciones para reducir ruido
      github-actions:
        patterns: ["*"]
    open-pull-requests-limit: 10

  # ─── npm / Node.js ─────────────────────────────────
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "tuesday"
      time: "09:00"
      timezone: "Europe/Madrid"
    labels:
      - "dependencies"
      - "javascript"
    commit-message:
      prefix: "chore"
      include: "scope"
    groups:
      # Actualizar todas las dependencias de desarrollo juntas
      dev-dependencies:
        dependency-type: "development"
        update-types: ["minor", "patch"]
      # Actualizar dependencias de producción individualmente (más cautela)
      production-minor-patch:
        dependency-type: "production"
        update-types: ["patch"]
    ignore:
      # No actualizar automáticamente major versions (requieren revisión)
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]
    open-pull-requests-limit: 10

  # ─── Python / pip ──────────────────────────────────
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "tuesday"
      time: "10:00"
      timezone: "Europe/Madrid"
    labels:
      - "dependencies"
      - "python"
    commit-message:
      prefix: "chore"
    groups:
      python-packages:
        patterns: ["*"]
        update-types: ["minor", "patch"]
    open-pull-requests-limit: 10

  # ─── Docker ────────────────────────────────────────
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "wednesday"
    labels:
      - "dependencies"
      - "docker"
    commit-message:
      prefix: "chore"

  # ─── Maven (Java) ──────────────────────────────────
  # Descomentar si el proyecto usa Java/Maven
  # - package-ecosystem: "maven"
  #   directory: "/"
  #   schedule:
  #     interval: "weekly"

  # ─── Gradle ────────────────────────────────────────
  # - package-ecosystem: "gradle"
  #   directory: "/"
  #   schedule:
  #     interval: "weekly"

  # ─── Go modules ────────────────────────────────────
  # - package-ecosystem: "gomod"
  #   directory: "/"
  #   schedule:
  #     interval: "weekly"
```

### 2.1 Configuración para monorepos

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/frontend"      # Aplicación frontend
    schedule:
      interval: "weekly"

  - package-ecosystem: "pip"
    directory: "/backend"       # Servicio Python
    schedule:
      interval: "weekly"

  - package-ecosystem: "docker"
    directory: "/infrastructure/docker"
    schedule:
      interval: "monthly"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## 3. Verificar que Dependabot está funcionando

### 3.1 Comprobar alertas activas

```bash
#!/usr/bin/env bash
REPO="${1:-jgutierrezdtt/mi-repo}"

echo "=== Dependabot Alerts: ${REPO} ==="

# Total por severidad
gh api "repos/${REPO}/dependabot/alerts?state=open&per_page=100" \
  --jq '
    group_by(.security_vulnerability.severity) |
    .[] |
    {
      severity: .[0].security_vulnerability.severity,
      count: length
    }
  '

echo ""
echo "=== Alertas Críticas y Altas ==="
gh api "repos/${REPO}/dependabot/alerts?state=open&severity=critical,high&per_page=20" \
  --jq '.[] | {
    number: .number,
    severity: .security_vulnerability.severity,
    package: .dependency.package.name,
    ecosystem: .dependency.package.ecosystem,
    cve: .security_advisory.cve_id,
    fixed_in: .security_vulnerability.first_patched_version.identifier
  }'
```

### 3.2 Listar PRs de Dependabot pendientes

```bash
gh pr list \
  --repo jgutierrezdtt/mi-repo \
  --author app/dependabot \
  --json number,title,createdAt,labels \
  --jq '.[] | {number:.number, title:.title, age:.createdAt}'
```

---

## 4. Política de gestión de alertas Dependabot

### 4.1 SLA recomendado para jgutierrezdtt

| Severidad | SLA de remediación |
|-----------|-------------------|
| 🔴 **Crítica** | 24 horas |
| 🟠 **Alta** | 72 horas |
| 🟡 **Media** | 2 semanas |
| 🔵 **Baja** | 1 mes o próximo ciclo de actualización |

### 4.2 Proceso cuando hay una alerta crítica

```
1. Dependabot alerta → notificación inmediata al equipo
2. Security-team evalúa el impacto real (¿es el código vulnerable accesible?)
3. Si vulnerable: PR de Dependabot se revisa y aprueba en <24h
4. Si no accesible: se documenta como "not exploitable" en el sistema de excepciones
5. Pipeline de Dependabot check reporta el estado en el PR
```

---

## 5. Integración con el pipeline de seguridad

El workflow `reusable/dependabot-check.yml` verifica el estado de Dependabot en cada PR:

```yaml
# En tu repo consumer — .github/workflows/security.yml
jobs:
  dependabot-check:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-dependabot-check.yml@main
    with:
      fail-on-critical: true   # Bloquear PR si hay alertas críticas sin resolver
      fail-on-high: true       # Bloquear PR si hay alertas altas sin resolver
      max-critical: 0          # Cero tolerancia para críticas
      max-high: 0              # Cero tolerancia para altas
    secrets:
      DEPENDABOT_CHECK_TOKEN: ${{ secrets.DEPENDABOT_CHECK_TOKEN }}
```

El token `DEPENDABOT_CHECK_TOKEN` es un Fine-grained PAT con:
- `Dependabot alerts`: Read-only
- `Metadata`: Read-only (implícito)

---

## 6. Ignorar alertas de Dependabot (con criterio)

Si una alerta no es explotable en tu contexto:

```bash
# Marcar alerta como "not exploitable" con comentario
gh api repos/jgutierrezdtt/mi-repo/dependabot/alerts/123 \
  -X PATCH \
  --field state=dismissed \
  --field dismissed_reason=not_used \
  --field dismissed_comment="La función vulnerable no es llamada desde código de producción. Verificado por el security-team el $(date +%Y-%m-%d)."
```

Las razones válidas de dismissal:
- `fix_started` — Fix en progreso
- `inaccurate` — Informe impreciso (falso positivo)
- `no_bandwidth` — Reconocido, sin capacidad para arreglar ahora
- `not_used` — La función vulnerable no se usa
- `tolerable_risk` — Riesgo aceptado explícitamente

---

## 7. Checklist

- [ ] **Dependabot alerts** habilitado en el repositorio
- [ ] **Dependabot security updates** habilitado
- [ ] `.github/dependabot.yml` presente y configurado para todos los ecosistemas usados
- [ ] **github-actions** incluido en dependabot.yml (para pinning de acciones)
- [ ] **DEPENDABOT_CHECK_TOKEN** configurado como secret del repositorio
- [ ] Workflow `reusable/dependabot-check.yml` llamado en el CI
- [ ] SLA de remediación documentado y comunicado al equipo
- [ ] Alertas críticas/altas resueltas en plazo
- [ ] No hay dismissals sin comentario justificativo

---

## Siguiente paso

➡️ [Tutorial 07 — Activación de Semgrep](07-semgrep-activation.md)
