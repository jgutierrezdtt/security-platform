# Tutorial 09 — Security Gates

> **Audiencia**: DevSecOps engineers, tech leads  
> **Nivel**: Intermedio-Avanzado  
> **Tiempo estimado**: 45 minutos

---

## ¿Qué es un Security Gate?

Un **Security Gate** es un punto de control automatizado en el pipeline de CI/CD que **bloquea el avance** del código si no cumple los estándares de seguridad definidos.

En `jgutierrezdtt`:

```
Commit → Tests → [SECURITY GATE] → Deploy
                       │
                  ¿Pasa el corte?
                  ├─ ✅ Sí → Continúa
                  └─ ❌ No → Pipeline falla, PR bloqueado
```

---

## 1. Política de Security Gates

### 1.1 Niveles de bloqueo

| Herramienta | Condición | Acción |
|------------|-----------|--------|
| **Semgrep** | ≥1 crítica (no exceptuada) | ❌ Bloquear siempre |
| **Semgrep** | ≥1 alta (no exceptuada) | ❌ Bloquear (configurable) |
| **Semgrep** | ≥1 media | ⚠️ Advertencia, no bloquea |
| **Dependabot** | ≥1 crítica sin resolver | ❌ Bloquear siempre |
| **Dependabot** | ≥1 alta sin resolver | ❌ Bloquear (configurable) |
| **Secret Scanning** | Secreto detectado | ❌ Bloquear (push protection) |
| **SLSA** | Provenance inválido | ❌ Bloquear en deploy |

### 1.2 Excepciones al bloqueo

El security gate se puede configurar en modo `report-only` para:
- Ramas de feature en repos que aún están onboarding el sistema
- Hotfixes urgentes (con proceso de post-mortem obligatorio)
- Ramas de demo/staging con aprobación explícita

```yaml
# Habilitar report-only para hotfixes
jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    with:
      report-only: ${{ contains(github.ref, 'hotfix/') }}
```

---

## 2. Configuración del Security Gate en Branch Protection

El security gate solo es efectivo si los status checks son **required** en la rama protegida. Sin esto, un desarrollador podría ignorar el fallo del pipeline y mergear igualmente.

### 2.1 Hacer los status checks obligatorios

```bash
# Los nombres de los status checks deben coincidir EXACTAMENTE con los job names
gh api repos/jgutierrezdtt/mi-repo/branches/main/protection \
  -X PUT \
  --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Semgrep SAST",
      "Dependabot Status"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

> **Importante**: Los nombres de los contextos (`"Semgrep SAST"`, `"Dependabot Status"`) deben coincidir **exactamente** con el campo `name` de los jobs en el workflow reutilizable.

### 2.2 Con Repository Rulesets (moderno)

```bash
gh api repos/jgutierrezdtt/mi-repo/rulesets \
  -X POST \
  --input - << 'EOF'
{
  "name": "security-gate",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main", "refs/heads/release/**"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "Semgrep SAST" },
          { "context": "Dependabot Status" }
        ]
      }
    }
  ]
}
EOF
```

---

## 3. Pipeline completo con Security Gate integrado

```yaml
# .github/workflows/security.yml — pipeline completo para repos consumer
name: Security Gate

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 3 * * 1"

permissions:
  contents: read

jobs:
  # ─── Gate 1: SAST con Semgrep ──────────────────────────────
  semgrep:
    name: Semgrep SAST          # ← Este nombre es el "context" en branch protection
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    with:
      scan-scope: ${{ github.event_name == 'pull_request' && 'diff' || 'full' }}
      fail-on-severity: high
      upload-sarif: true
      report-only: ${{ github.event.pull_request.draft == true }}
    secrets:
      SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}
      EXCEPTIONS_READER_TOKEN: ${{ secrets.EXCEPTIONS_READER_TOKEN }}

  # ─── Gate 2: Dependencias vulnerables ─────────────────────
  dependabot:
    name: Dependabot Status     # ← Este nombre es el "context" en branch protection
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/dependabot-check.yml@main
    with:
      fail-on-critical: true
      fail-on-high: true
      max-critical: 0
      max-high: 0
    secrets:
      DEPENDABOT_CHECK_TOKEN: ${{ secrets.DEPENDABOT_CHECK_TOKEN }}

  # ─── Gate 3: Validación final (solo si pasan los anteriores)
  security-summary:
    name: Security Gate Summary
    needs: [semgrep, dependabot]
    runs-on: ubuntu-latest
    if: always()

    steps:
      - name: Evaluate security gate result
        env:
          SEMGREP_RESULT: ${{ needs.semgrep.result }}
          DEPENDABOT_RESULT: ${{ needs.dependabot.result }}
          SEMGREP_CRITICAL: ${{ needs.semgrep.outputs.critical-count }}
          SEMGREP_HIGH: ${{ needs.semgrep.outputs.high-count }}
          DEPENDABOT_CRITICAL: ${{ needs.dependabot.outputs.critical-alerts }}
          DEPENDABOT_HIGH: ${{ needs.dependabot.outputs.high-alerts }}
        run: |
          cat >> "$GITHUB_STEP_SUMMARY" << SUMMARY
          ## 🚦 Security Gate — Resumen Final

          | Check | Estado | Críticas | Altas |
          |-------|--------|----------|-------|
          | Semgrep SAST | $([ "${SEMGREP_RESULT}" = "success" ] && echo "✅ Aprobado" || echo "❌ Fallido") | ${SEMGREP_CRITICAL:-?} | ${SEMGREP_HIGH:-?} |
          | Dependabot | $([ "${DEPENDABOT_RESULT}" = "success" ] && echo "✅ Aprobado" || echo "❌ Fallido") | ${DEPENDABOT_CRITICAL:-?} | ${DEPENDABOT_HIGH:-?} |
          SUMMARY

          # El gate falla si cualquier check falló
          if [[ "${SEMGREP_RESULT}" != "success" || "${DEPENDABOT_RESULT}" != "success" ]]; then
            echo "❌ Security Gate fallido. No se puede mergear hasta resolver los problemas de seguridad."
            echo ""
            echo "Pasos para resolver:"
            echo "1. Revisa los hallazgos en los comentarios del PR"
            echo "2. Corrige las vulnerabilidades en el código"
            echo "3. Si crees que es un falso positivo, abre un issue en jgutierrezdtt/security-exceptions"
            echo "4. Los cambios en dependencias vulnerables deben actualizarse via Dependabot PRs"
            exit 1
          fi

          echo "✅ Security Gate aprobado. Todos los checks de seguridad han pasado."
```

---

## 4. Security Gate para deploys a producción

En el deploy, añade una verificación adicional de provenance SLSA:

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  release:
    types: [published]

jobs:
  security-pre-deploy-check:
    name: Pre-Deploy Security Check
    runs-on: ubuntu-latest
    steps:
      - name: Verify no open critical alerts
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          CRITICAL=$(gh api repos/${{ github.repository }}/dependabot/alerts \
            --jq '[.[] | select(.state == "open" and .security_vulnerability.severity == "critical")] | length')
          
          if [[ "$CRITICAL" -gt 0 ]]; then
            echo "❌ Deploy bloqueado: ${CRITICAL} alerta(s) crítica(s) de Dependabot sin resolver"
            exit 1
          fi
          echo "✅ Sin alertas críticas de Dependabot"

      - name: Verify SLSA provenance (if applicable)
        run: |
          # Verificar que el artefacto tiene provenance válido
          # (ver Tutorial 05 para implementación completa)
          echo "→ Verificando provenance SLSA..."

  deploy:
    needs: [security-pre-deploy-check]
    # ... resto del deploy
```

---

## 5. Alertas y notificaciones del Security Gate

```yaml
# Notificar al canal de Slack cuando el security gate falla en main
- name: Notify Slack on security gate failure
  if: failure() && github.ref == 'refs/heads/main'
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "🚨 Security Gate fallido en *${{ github.repository }}*",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "🚨 *Security Gate fallido*\n*Repo*: ${{ github.repository }}\n*Branch*: ${{ github.ref_name }}\n*Commit*: ${{ github.sha }}\n*Detalles*: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_SECURITY_WEBHOOK }}
```

---

## 6. Checklist

- [ ] Status checks `Semgrep SAST` y `Dependabot Status` configurados como **required** en branch protection
- [ ] `enforce_admins: true` — los admins también cumplen las reglas
- [ ] Draft PRs en modo **report-only** (para feedback temprano sin bloqueo)
- [ ] Security gate falla si hay **críticas o altas** sin excepciones aprobadas
- [ ] Notificaciones configuradas para fallos del security gate en `main`
- [ ] Proceso de **hotfix** documentado y controlado (con post-mortem)
- [ ] Pre-deploy check en pipelines de producción

---

## Siguiente paso

➡️ [Tutorial 10 — Reporting de Seguridad](10-reporting.md)
