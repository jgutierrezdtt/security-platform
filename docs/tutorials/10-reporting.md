# Tutorial 10 — Reporting de Seguridad

> **Audiencia**: Security team, Engineering Managers, CISO  
> **Nivel**: Intermedio  
> **Tiempo estimado**: 60 minutos

---

## ¿Qué cubre este tutorial?

El sistema de reporting de seguridad de `jgutierrezdtt` genera:

1. **Comentarios visuales en PRs** — tabla de hallazgos por each scan
2. **Job Summaries** — resumen visual en la pestaña Actions de GitHub
3. **Dashboard en README** — estado de seguridad por repositorio y rama
4. **Reporte semanal** — enviado por workflow automatizado

---

## 1. Comentarios en Pull Requests

El workflow reutilizable genera automáticamente un comentario en cada PR con los resultados de Semgrep. El comentario usa la acción `marocchino/sticky-pull-request-comment` para actualizar el mismo comentario en cada push (no crea spam).

**Ejemplo de comentario generado:**

```markdown
## 🔍 Semgrep Security Scan — Resultados

**Repositorio**: `jgutierrezdtt/frontend-app` | **Rama**: `feature/user-auth` | **Commit**: `a1b2c3d4` | **Fecha**: 2026-05-10 01:30 UTC

### Estado: 🟠 BLOQUEADO — Vulnerabilidades Altas

### 📊 Resumen

| 🔴 Críticas | 🟠 Altas | 🟡 Medias | 🔵 Bajas | ⚪ Info | ✅ Exceptuadas |
|:-----------:|:--------:|:---------:|:--------:|:-------:|:-------------:|
| **0** | **2** | 3 | 1 | 0 | 1 |

### 🚨 Hallazgos Activos

| # | Severidad | Regla | Archivo | Línea | Descripción |
|---|-----------|-------|---------|-------|-------------|
| 1 | 🟠 HIGH | `sql-injection-string-concat` | `src/db/queries.js` | 45 | SQL injection via concatenación... |
| 2 | 🟠 HIGH | `no-hardcoded-api-keys` | `config/settings.py` | 12 | Posible credencial en API_KEY... |
| 3 | 🟡 MEDIUM | `debug-mode-production` | `.env` | 3 | DEBUG=True detectado |
```

### 1.1 Personalizar el comentario

Para personalizar el template del comentario, edita el script Python en `reusable/semgrep-scan.yml` en la sección `Process results and apply exceptions`.

---

## 2. GitHub Actions Job Summary

Cada ejecución del workflow genera un summary visible en la pestaña **Actions**:

```yaml
# El workflow escribe en GITHUB_STEP_SUMMARY
- name: Write step summary
  run: |
    cat >> "$GITHUB_STEP_SUMMARY" << 'EOF'
    ## 🔍 Semgrep — Resumen del Análisis

    | Métrica | Valor |
    |---------|-------|
    | Archivos analizados | 247 |
    | Reglas aplicadas | 1,432 |
    | Tiempo de análisis | 45s |
    | Hallazgos totales | 5 |
    | Exceptuados | 1 |
    | **Hallazgos activos** | **4** |

    [Ver reporte completo en el artefacto](../../../actions/runs/${{ github.run_id }})
    EOF
```

---

## 3. Dashboard en el README de security-platform

### 3.1 Workflow de generación automática

```yaml
# .github/workflows/org-security-report.yml
name: Generate Org Security Dashboard

on:
  schedule:
    - cron: "0 2 * * 0"  # Domingo 02:00 UTC
  workflow_dispatch:

permissions:
  contents: write  # Para hacer commit del README actualizado

jobs:
  generate-report:
    name: Generate Security Dashboard
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Generate dashboard
        env:
          GH_TOKEN: ${{ secrets.ORG_SECURITY_REPORT_TOKEN }}
          ORG: jgutierrezdtt
        run: |
          python3 scripts/generate-org-report.py \
            --org "$ORG" \
            --output-file README.md \
            --repos-list config/monitored-repos.txt

      - name: Commit updated dashboard
        run: |
          git config --global user.name "security-bot[bot]"
          git config --global user.email "security-bot@jgutierrezdtt.com"
          
          if git diff --quiet README.md; then
            echo "No changes to dashboard"
          else
            git add README.md
            git commit -m "docs: update security dashboard [skip ci]"
            git push
          fi
```

### 3.2 Script de generación del dashboard

```python
#!/usr/bin/env python3
# scripts/generate-org-report.py
"""
Genera el dashboard de seguridad de la organización consultando la GitHub API.
Actualiza la sección de tabla del README.md.
"""

import os
import sys
import json
import argparse
import urllib.request
from datetime import datetime, timezone

def gh_api(path, token, params=""):
    url = f"https://api.github.com{path}"
    if params:
        url += f"?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"API error for {path}: {e}", file=sys.stderr)
        return None

def get_dependabot_status(repo, token):
    alerts = gh_api(f"/repos/{repo}/dependabot/alerts", token, "state=open&per_page=100")
    if alerts is None:
        return "❌", 0, 0
    critical = sum(1 for a in alerts if a.get("security_vulnerability", {}).get("severity") == "critical")
    high = sum(1 for a in alerts if a.get("security_vulnerability", {}).get("severity") == "high")
    status = "✅ Activo" if isinstance(alerts, list) else "❌ Error"
    return status, critical, high

def get_code_scanning_status(repo, token):
    alerts = gh_api(f"/repos/{repo}/code-scanning/alerts", token, "state=open&per_page=100")
    if alerts is None:
        return "❌", 0, 0
    critical = sum(1 for a in alerts if a.get("rule", {}).get("security_severity_level") == "critical")
    high = sum(1 for a in alerts if a.get("rule", {}).get("security_severity_level") == "high")
    return "✅ Activo", critical, high

def get_last_scan_date(repo, token):
    runs = gh_api(f"/repos/{repo}/actions/runs", token, "event=schedule&per_page=1")
    if runs and runs.get("workflow_runs"):
        created = runs["workflow_runs"][0].get("created_at", "")
        if created:
            return created[:10]
    return "N/A"

def generate_table(repos, token):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    lines = [
        f"> **Actualizado automáticamente** el {now}",
        "",
        "### Resumen por repositorio",
        "",
        "| Repositorio | Rama | Semgrep | Dependabot | SLSA | Críticas | Altas | Medias | Último Análisis |",
        "|-------------|------|---------|------------|------|----------|-------|--------|-----------------|",
    ]
    
    for repo in repos:
        repo = repo.strip()
        if not repo or repo.startswith("#"):
            continue
        
        # Obtener información del repo
        repo_info = gh_api(f"/repos/{repo}", token)
        default_branch = repo_info.get("default_branch", "main") if repo_info else "main"
        
        # Obtener estado de Dependabot
        dep_status, dep_critical, dep_high = get_dependabot_status(repo, token)
        
        # Obtener estado de Code Scanning (Semgrep)
        scan_status, scan_critical, scan_high = get_code_scanning_status(repo, token)
        
        # Total de críticas y altas
        total_critical = dep_critical + scan_critical
        total_high = dep_high + scan_high
        
        # Fecha del último análisis
        last_scan = get_last_scan_date(repo, token)
        
        # Estado SLSA
        slsa_status = "✅ L3" if "security-platform" in repo else "⚠️ Pendiente"
        
        repo_name = repo.split("/")[-1]
        repo_url = f"https://github.com/{repo}"
        
        lines.append(
            f"| [`{repo_name}`]({repo_url}) | `{default_branch}` "
            f"| {scan_status} | {dep_status} | {slsa_status} "
            f"| **{total_critical}** | **{total_high}** | — | {last_scan} |"
        )
    
    return "\n".join(lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--repos-list", required=True)
    args = parser.parse_args()
    
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("Error: GH_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    with open(args.repos_list) as f:
        repos = f.readlines()
    
    table = generate_table(repos, token)
    
    # Actualizar el README entre los marcadores
    with open(args.output_file) as f:
        content = f.read()
    
    # Reemplazar entre marcadores HTML
    start_marker = "<!-- SECURITY_DASHBOARD_START -->"
    end_marker = "<!-- SECURITY_DASHBOARD_END -->"
    
    if start_marker in content and end_marker in content:
        before = content.split(start_marker)[0]
        after = content.split(end_marker)[1]
        new_content = f"{before}{start_marker}\n{table}\n{end_marker}{after}"
        
        with open(args.output_file, "w") as f:
            f.write(new_content)
        print(f"✅ Dashboard actualizado en {args.output_file}")
    else:
        print(f"❌ Marcadores no encontrados en {args.output_file}", file=sys.stderr)
        sys.exit(1)
```

### 3.3 Lista de repos monitoreados

```
# config/monitored-repos.txt
# Un repositorio por línea (formato: org/repo)
# Las líneas que empiezan con # son comentarios

jgutierrezdtt/security-platform
jgutierrezdtt/security-exceptions
# Añadir más repos aquí cuando se incorporen al sistema
```

---

## 4. Artefactos de reporte

Cada ejecución de Semgrep genera y sube los siguientes artefactos:

| Artefacto | Contenido | Retención |
|-----------|-----------|-----------|
| `semgrep-results-{run_number}` | JSON + SARIF + Markdown | 90 días |
| SARIF en Security tab | Alertas integradas en GitHub | Permanente (hasta cierre) |

---

## 5. Métricas de tendencia (OpenSSF Scorecard)

El workflow de Scorecard genera una puntuación de seguridad para cada repositorio:

```bash
# Ver la puntuación actual del repo
gh api repos/jgutierrezdtt/security-platform/code-scanning/alerts \
  --jq '[.[] | select(.tool.name == "scorecard")] | length'
```

Los resultados se publican en [securityscorecards.dev](https://securityscorecards.dev) (solo para repos públicos) o en el Security tab del repositorio.

---

## 6. Checklist

- [ ] Workflow `org-security-report.yml` creado y programado semanalmente
- [ ] `config/monitored-repos.txt` actualizado con todos los repos
- [ ] `ORG_SECURITY_REPORT_TOKEN` configurado como secret del repositorio
- [ ] Marcadores `<!-- SECURITY_DASHBOARD_START -->` y `<!-- SECURITY_DASHBOARD_END -->` en el README
- [ ] OpenSSF Scorecard ejecutándose semanalmente
- [ ] Comentarios de PR habilitados en el workflow reutilizable
- [ ] Job summaries funcionando correctamente

---

## 🎉 Has completado los tutoriales de configuración

### Resumen de lo implementado

| Tutorial | Componente | Estado |
|----------|-----------|--------|
| 01 | Protección de repositorios (GHAS, Secret Scanning) | ✅ |
| 02 | Branch protection con Rulesets | ✅ |
| 03 | Roles, teams y permisos | ✅ |
| 04 | CODEOWNERS y PR approvals | ✅ |
| 05 | SLSA Level 3 | ✅ |
| 06 | Dependabot | ✅ |
| 07 | Semgrep SAST | ✅ |
| 08 | Gestión de excepciones | ✅ |
| 09 | Security Gates | ✅ |
| 10 | Reporting | ✅ |

### Próximos pasos recomendados

1. **Incorporar nuevos repos**: Usa `security-consumer-template` como base para nuevos repos o copia `.github/workflows/security.yml` en repos existentes
2. **Revisar excepciones existentes**: Asegúrate de que ninguna haya expirado
3. **Configurar notificaciones**: Integra el reporting con Slack, Teams o email
4. **Revisar el OpenSSF Scorecard**: Mejorar la puntuación de cada repositorio
5. **Evaluar SLSA L4**: Cuando el ecosistema madure, considerar builds herméticos con Bazel

---

## Siguiente paso

➡️ [Tutorial 11 — Gobierno de Vulnerabilidades](11-vulnerability-governance.md) — SLAs, ownership, escalado, compliance y métricas del programa
